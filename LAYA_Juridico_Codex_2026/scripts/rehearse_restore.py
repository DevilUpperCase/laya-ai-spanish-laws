"""Real encrypted snapshot/private-schema restoration with a synthetic deletion canary.

Creates an isolated rehearsal database; never restores over the live database.
"""
import argparse,asyncio,io,json,os,re,subprocess,sys,tarfile,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4,UUID
import httpx,psycopg,pymupdf
from psycopg import sql
from psycopg.conninfo import make_conninfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.api.app.deletion_journal import read_journal
from scripts.reapply_deletions import reapply
from scripts.backup_local import snapshot,manifest,verified_plaintext,KEY
from scripts.scheduled_backup import paused_snapshot


class PlainReader(io.RawIOBase):
    def __init__(self,blocks):self.blocks=iter(blocks);self.pending=b''
    def readable(self):return True
    def readinto(self,buffer):
        if not self.pending:
            try:self.pending=next(self.blocks)
            except StopIteration:return 0
        count=min(len(buffer),len(self.pending));buffer[:count]=self.pending[:count];self.pending=self.pending[count:];return count


def wait_paused():
    for _ in range(45):
        path=ROOT/'private-data/runtime/status.json'
        if path.exists():
            status=json.loads(path.read_text())
            if all(status['services'][n]['state']=='paused' for n in ('api','worker')):return
        time.sleep(2)
    raise RuntimeError('Supervisor did not pause private services')


def restore_private(folder,database,objects):
    if not re.fullmatch(r'laya_rehearsal_[0-9a-f]{16}',database):raise ValueError('Isolated rehearsal database required')
    key=KEY.read_bytes();payload=manifest(folder,key)
    # All encrypted files authenticate before any restoration command.
    for name in payload['files']:
        for _ in verified_plaintext(folder/name,key):pass
    target=make_conninfo(Settings().admin_database_url,dbname=database)
    # pg_restore's --schema filter selects schema contents, not the CREATE SCHEMA entry.
    # Private vector columns also depend on the public pgvector extension.
    with psycopg.connect(target) as conn:
        conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
        conn.execute('CREATE SCHEMA IF NOT EXISTS private')
        conn.execute('CREATE SCHEMA IF NOT EXISTS browser_auth')
        conn.execute('CREATE SCHEMA IF NOT EXISTS legal')
        conn.execute('CREATE TABLE IF NOT EXISTS legal.section_versions(id text PRIMARY KEY)')
        conn.execute('CREATE TEMP TABLE rehearsal_section_ids(id text PRIMARY KEY) ON COMMIT DROP')
        # Public citation stubs only: scoped private recovery is not a legal-corpus restore.
        with psycopg.connect(Settings().admin_database_url) as source:
            with source.cursor(name='citation_ids') as cursor:
                cursor.execute('SELECT id FROM legal.section_versions')
                with conn.cursor().copy('COPY rehearsal_section_ids(id) FROM STDIN') as copied:
                    for row in cursor:copied.write_row(row)
        conn.execute('''INSERT INTO legal.section_versions(id) SELECT id FROM rehearsal_section_ids
         ON CONFLICT(id) DO NOTHING''')
    command=['docker','exec','-i','laya-juridico-db-1','pg_restore','-U','postgres','-d',database,'--single-transaction','--exit-on-error','--schema=private','--schema=browser_auth']
    child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    try:
        for block in verified_plaintext(folder/'app.pg.enc',key):child.stdin.write(block)
        child.stdin.close()
        if child.wait()!=0:raise RuntimeError('Private database restore failed')
    except BaseException:child.kill();child.wait();raise
    with psycopg.connect(target) as conn:
        conn.execute('GRANT USAGE ON SCHEMA private TO laya_api,laya_worker')
        conn.execute('GRANT USAGE ON SCHEMA browser_auth TO laya_api')
    with io.BufferedReader(PlainReader(verified_plaintext(folder/'objects.tar.enc',key))) as stream,tarfile.open(fileobj=stream,mode='r|') as archive:
        for member in archive:
            if not member.isfile() or member.issym() or member.islnk():raise ValueError('Unsafe storage archive member')
            destination=(objects/member.name.replace('\\','/')).resolve()
            if not destination.is_relative_to(objects.resolve()):raise ValueError('Storage archive escaped rehearsal directory')
            destination.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(member) as src,destination.open('wb') as out:
                for data in iter(lambda:src.read(512*1024),b''):out.write(data)


def apply_private_rehearsal_migrations(database):
    """Upgrade the restored private schema without restoring the legal corpus."""
    target=make_conninfo(Settings().admin_database_url,dbname=database)
    applied=[]
    # These are the private-document/library/retrieval/worker migrations.
    # Other migrations alter the legal corpus and are outside this rehearsal.
    with psycopg.connect(target) as conn:
        has_trash=conn.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='private' AND table_name='documents' AND column_name='trashed_at'").fetchone()
        if not has_trash:
            conn.execute((ROOT/'db/migrations/013_document_library.sql').read_text(encoding='utf-8'))
            applied.append('013_document_library.sql')
        has_passages=conn.execute("SELECT to_regclass('private.passage_index')").fetchone()[0]
        if has_passages is None:
            conn.execute((ROOT/'db/migrations/015_private_retrieval.sql').read_text(encoding='utf-8'))
            applied.append('015_private_retrieval.sql')
        has_scoped_worker=conn.execute("SELECT to_regprocedure('private.lease_document_job(uuid)')").fetchone()[0]
        if has_scoped_worker is None:
            conn.execute((ROOT/'db/migrations/017_scoped_worker.sql').read_text(encoding='utf-8'))
            applied.append('017_scoped_worker.sql')
        # GRANT is idempotent and completes the current index-worker contract.
        conn.execute((ROOT/'db/migrations/018_worker_index_queue.sql').read_text(encoding='utf-8'))
        applied.append('018_worker_index_queue.sql')
    return applied


async def purge_and_verify(settings,document,tenant,token):
    from services.api.app.database import Database
    from services.api.app.jobs import JobWorker
    from services.api.app.main import create_app
    app=create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local-test',headers={'Authorization':'Bearer '+token,'X-Tenant-ID':str(tenant)}) as client:
            assert (await client.get('/v1/documents/'+str(document))).status_code==404
            assert (await client.get('/v1/documents/'+str(document)+'/download')).status_code==404
    worker_db=Database(settings.worker_database_url,worker=True);await worker_db.open()
    try:
        worker=JobWorker(worker_db,settings)
        for _ in range(100):
            if not await worker.run_once(document):break
        async with worker_db.pool.connection() as conn:
            # Restricted worker reads require active-tenant context.
            await conn.execute("SELECT set_config('app.tenant_id',%s,true)",(str(tenant),))
            row=await (await conn.execute('SELECT purged_at FROM private.documents WHERE id=%s',(document,))).fetchone()
            assert row and row['purged_at']
    finally:await worker_db.close()


def prepare_snapshot(settings,session):
    for _ in range(60):
        try:
            if httpx.get('http://127.0.0.1:8000/health',trust_env=False,timeout=2).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(2)
    else:raise RuntimeError('API did not become available for rehearsal')
    headers={'Authorization':'Bearer '+session['token'],'X-Tenant-ID':session['tenant_id']}
    pdf=pymupdf.open();page=pdf.new_page();page.insert_text((72,72),'RESTORE_REHEARSAL_CANARY. Arrendamiento de vivienda.');data=pdf.tobytes();pdf.close()
    with httpx.Client(base_url='http://127.0.0.1:8000',headers=headers,trust_env=False,timeout=30) as client:
        r=client.post('/v1/documents',files={'file':('restore-synthetic.pdf',data,'application/pdf')},headers={'Idempotency-Key':'restore-'+uuid4().hex});r.raise_for_status();document=r.json()['id']
        for _ in range(60):
            r=client.get('/v1/documents/'+document);r.raise_for_status()
            if r.json()['parse_status']=='ready':break
            if r.json()['parse_status']=='failed':raise RuntimeError('Synthetic canary extraction failed')
            time.sleep(2)
        else:raise RuntimeError('Synthetic canary extraction deadline')
    print('Synthetic canary extracted. Pausing private services for encrypted snapshot.',flush=True)
    folder=paused_snapshot()
    print('Encrypted snapshot created; live services resuming.',flush=True)
    for _ in range(60):
        try:
            if httpx.get('http://127.0.0.1:8000/health',trust_env=False,timeout=2).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(2)
    deleted_start=time.monotonic()
    with httpx.Client(base_url='http://127.0.0.1:8000',headers=headers,trust_env=False,timeout=30) as client:
        r=client.delete('/v1/documents/'+document);r.raise_for_status()
        assert client.get('/v1/documents/'+document).status_code==404
    with psycopg.connect(settings.admin_database_url) as conn:
        key=conn.execute('SELECT object_key FROM private.documents WHERE id=%s',(document,)).fetchone()[0]
    live_object=settings.private_storage_path/key
    for _ in range(60):
        if not live_object.exists():break
        time.sleep(2)
    if live_object.exists():raise RuntimeError('Live canary purge deadline')
    purge_seconds=time.monotonic()-deleted_start
    state={'folder':folder.name,'document':document,'tenant':session['tenant_id'],'object_key':key,'purge_seconds':purge_seconds,'database':'laya_rehearsal_'+uuid4().hex[:16]}
    (ROOT/'private-data/runtime/restore-state.json').write_text(json.dumps(state))
    return state


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    settings=Settings();session=json.loads((ROOT/'private-data/local-session.json').read_text())
    state=json.loads((ROOT/'private-data/runtime/restore-state.json').read_text()) if args.resume else prepare_snapshot(settings,session)
    database=state['database']
    if not re.fullmatch(r'laya_rehearsal_[0-9a-f]{16}',database):raise ValueError('Invalid isolated database')
    folder=ROOT/'private-data/backups'/state['folder'];document=state['document'];key=state['object_key'];purge_seconds=state['purge_seconds']
    objects=ROOT/'private-data/restore-rehearsals'/database/'objects';objects.mkdir(parents=True,exist_ok=True)
    target=make_conninfo(settings.admin_database_url,dbname=database)
    with psycopg.connect(settings.admin_database_url,autocommit=True) as conn:
        if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(database,)).fetchone():conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    state_path=ROOT/'private-data/runtime/restore-state.json'
    if not state.get('private_restored'):
        print('Restoring private schemas into isolated rehearsal database.',flush=True)
        restore_private(folder,database,objects)
        state['private_restored']=True
        state_path.write_text(json.dumps(state))
    if not state.get('private_schema_upgraded'):
        print('Applying current private-schema recovery migrations.',flush=True)
        state['private_migrations_applied']=apply_private_rehearsal_migrations(database)
        state['private_schema_upgraded']=True
        state_path.write_text(json.dumps(state))
    if state.get('barrier_applied'):
        with psycopg.connect(target) as conn:
            after=conn.execute('SELECT deleted_at FROM private.documents WHERE id=%s',(document,)).fetchone()
            assert after and after[0] is not None
    else:
        with psycopg.connect(target) as conn:
            before=conn.execute('SELECT deleted_at FROM private.documents WHERE id=%s',(document,)).fetchone()
            assert before and before[0] is None and (objects/key).is_file()
            records=read_journal(settings.deletion_journal_path);reapply(conn,records);conn.execute('DELETE FROM browser_auth.sessions');conn.commit()
        state['canary_existed_before_barrier']=True
        state['barrier_applied']=True
        state_path.write_text(json.dumps(state))
    restored=settings.model_copy(update={'database_url':make_conninfo(settings.database_url,dbname=database),'worker_database_url':make_conninfo(settings.worker_database_url,dbname=database),'private_storage_path':objects})
    asyncio.run(purge_and_verify(restored,UUID(document),UUID(session['tenant_id']),session['token']),loop_factory=asyncio.SelectorEventLoop if os.name=='nt' else asyncio.new_event_loop)
    assert not (objects/key).exists()
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'passed','scope':'real_encrypted_snapshot_and_private_schema_restore','snapshot':folder.name,'private_schema_migrations_applied':state.get('private_migrations_applied',[]),'live_purge_seconds':purge_seconds,'restored_live_canary_before_barrier':bool(state.get('canary_existed_before_barrier')),'restored_read_and_download_denied':True,'restored_object_purged':True,'browser_sessions_invalidated':True,'limitations':['Synthetic canary only; private schemas restored and upgraded in an isolated database. The legal corpus and Auth database were not restored. Independent journal replication, key custody and 30-day elapsed expiry proof remain pending.']}
    (ROOT/'verification/reports/restore-rehearsal.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
