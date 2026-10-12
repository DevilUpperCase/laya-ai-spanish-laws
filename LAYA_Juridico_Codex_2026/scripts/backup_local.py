"""Authenticated encrypted local backups. Separate key custody/off-host replication still required."""
import argparse,hashlib,hmac,io,json,os,re,secrets,struct,subprocess,sys,tarfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.runtime_lock import RuntimeLock

MAGIC=b'LAYABKP2';BLOCK=512*1024
BACKUPS=ROOT/'private-data/backups';KEY=ROOT/'private-data/backup-keys/master.key'


def encrypt_stream(stream,path,key):
    """Each block and the end marker authenticate their position and unique nonce."""
    cipher=AESGCM(key);prefix=secrets.token_bytes(8);temporary=path.with_suffix('.partial')
    try:
        with temporary.open('wb') as out:
            out.write(MAGIC+prefix);index=0
            while True:
                data=stream.read(BLOCK);counter=struct.pack('!I',index);final=not data
                encrypted=cipher.encrypt(prefix+counter,data,MAGIC+prefix+counter+bytes([final]))
                out.write(struct.pack('!I',len(data))+encrypted)
                index+=1
                if final:break
            out.flush();os.fsync(out.fileno())
        temporary.replace(path)
    except BaseException:temporary.unlink(missing_ok=True);raise


def _blocks(stream,key):
    header=stream.read(16)
    if len(header)!=16 or header[:8]!=MAGIC:raise ValueError('Invalid encrypted backup header')
    cipher=AESGCM(key);prefix=header[8:];index=0
    while True:
        raw_length=stream.read(4)
        if len(raw_length)!=4:raise ValueError('Missing authenticated end marker')
        length=struct.unpack('!I',raw_length)[0]
        if length>BLOCK:raise ValueError('Encrypted block exceeds budget')
        data=stream.read(length+16)
        if len(data)!=length+16:raise ValueError('Truncated encrypted backup')
        counter=struct.pack('!I',index)
        plain=cipher.decrypt(prefix+counter,data,MAGIC+prefix+counter+bytes([length==0]))
        index+=1
        if length==0:
            if stream.read(1):raise ValueError('Trailing encrypted backup data')
            return
        yield plain


def verified_plaintext(path,key):
    """Verify the entire snapshot before releasing content, then verify every block again."""
    if path.is_symlink():raise ValueError('Symlinked encrypted backup prohibited')
    with path.open('rb') as stream:
        for _ in _blocks(stream,key):pass
        stream.seek(0)
        yield from _blocks(stream,key)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda:stream.read(BLOCK),b''):h.update(data)
    return h.hexdigest()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def manifest(folder,key):
    if folder.is_symlink() or not folder.resolve().is_relative_to(BACKUPS.resolve()):raise ValueError('Snapshot outside owned backup directory')
    envelope=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));payload=envelope['payload']
    if not hmac.compare_digest(envelope['hmac_sha256'],hmac.new(key,canonical(payload),hashlib.sha256).hexdigest()):raise ValueError('Manifest authentication failed')
    for name,sha in payload['files'].items():
        if not re.fullmatch(r'[a-z][a-z0-9.-]+\.enc',name):raise ValueError('Invalid snapshot artifact path')
        path=folder/name
        if path.is_symlink() or digest(path)!=sha:raise ValueError('Snapshot artifact integrity failed')
    return payload


def snapshot(*,database=None,objects=None):
    BACKUPS.mkdir(parents=True,exist_ok=True)
    with RuntimeLock(BACKUPS/'backup.lock'):
        return _snapshot_locked(database=database,objects=objects)


def _snapshot_locked(*,database=None,objects=None):
    from services.api.app.config import Settings
    settings=Settings()
    if not KEY.is_file():
        KEY.parent.mkdir(parents=True,exist_ok=True)
        with KEY.open('xb') as out:out.write(secrets.token_bytes(32));out.flush();os.fsync(out.fileno())
    key=KEY.read_bytes();BACKUPS.mkdir(parents=True,exist_ok=True)
    if database and not re.fullmatch(r'laya_rehearsal_[0-9a-f]{16}',database):raise ValueError('Rehearsal database name required')
    if not database:
        # Snapshot only while this project's API and document worker are paused.
        state_path=ROOT/'private-data/runtime/status.json'
        state=json.loads(state_path.read_text())
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(state['generated_at'])).total_seconds()
        if not (ROOT/'private-data/runtime/maintenance').is_file() or age>20 or any(state['services'][s]['state']!='paused' for s in ('api','worker')):
            raise RuntimeError('Pause the local stack and wait for paused API/worker status')
    now=datetime.now(timezone.utc);folder=BACKUPS/(now.strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:16]);folder.mkdir()
    files={}
    for db,name in ([(database,'app')] if database else [('laya_juridico','app'),('laya_auth','auth')]):
        path=folder/(name+'.pg.enc')
        child=subprocess.Popen(['docker','exec','laya-juridico-db-1','pg_dump','-U','postgres','-d',db,'--format=custom','--compress=3'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:encrypt_stream(child.stdout,path,key)
        except BaseException:child.kill();child.wait();raise
        if child.wait()!=0:raise RuntimeError('Database snapshot failed')
        files[path.name]=digest(path)
    for name,source in [('objects',objects or settings.private_storage_path),('legal-originals',None if database else settings.public_storage_path)]:
        if source is None:continue
        source=Path(source).resolve()
        if not source.is_relative_to((ROOT/'private-data').resolve()):raise ValueError('Snapshot source outside project private storage')
        read_fd,write_fd=os.pipe()
        # Streaming tar producer writes no plaintext archive to disk.
        import threading
        errors=[]
        def produce():
            try:
                with os.fdopen(write_fd,'wb') as out,tarfile.open(fileobj=out,mode='w|') as archive:
                    for item in source.rglob('*'):
                        if item.is_symlink():raise ValueError('Symlink in snapshot source')
                        if item.is_file():archive.add(item,arcname=str(item.relative_to(source)),recursive=False)
            except BaseException as e:errors.append(type(e).__name__)
        thread=threading.Thread(target=produce);thread.start();path=folder/(name+'.tar.enc')
        with os.fdopen(read_fd,'rb') as stream:encrypt_stream(stream,path,key)
        thread.join()
        if errors:raise RuntimeError('Storage snapshot failed')
        files[path.name]=digest(path)
    payload={'format':'laya-encrypted-backup-v2','created_at':now.isoformat(),'expires_at':(now+timedelta(days=30)).isoformat(),'files':files,'status':'complete','scope':'local_rehearsal' if database else 'local_application','limitations':['Key and snapshots are on this host; independent encrypted replication/key custody and 30-day elapsed expiry evidence remain pending.','Restore must use the current independent deletion journal and invalidate browser sessions before access.']}
    envelope={'payload':payload,'hmac_sha256':hmac.new(key,canonical(payload),hashlib.sha256).hexdigest()}
    temporary=folder/'manifest.tmp';temporary.write_text(json.dumps(envelope,indent=2)+'\n');temporary.replace(folder/'manifest.json')
    return folder


def expire():
    BACKUPS.mkdir(parents=True,exist_ok=True)
    key=KEY.read_bytes();deleted=0;issues=[]
    with RuntimeLock(BACKUPS/'backup.lock'):
        for folder in BACKUPS.iterdir():
            if not folder.is_dir() or not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{16}',folder.name):continue
            try:
                if not (folder/'manifest.json').is_file():raise ValueError('Incomplete snapshot requires operator review')
                payload=manifest(folder,key)
                if datetime.fromisoformat(payload['expires_at'])>datetime.now(timezone.utc):continue
                # Delete only authenticated owned artifact names; never recursively delete a computed path.
                if set(p.name for p in folder.iterdir())!=set(payload['files'])|{'manifest.json'}:raise ValueError('Unexpected snapshot files; operator review required')
                for name in payload['files']:(folder/name).unlink()
                (folder/'manifest.json').unlink();folder.rmdir();deleted+=1
            except (ValueError,OSError,KeyError,TypeError) as error:issues.append({'snapshot':folder.name,'failure_code':type(error).__name__})
        report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'requires_operator_review' if issues else 'passed','expired_snapshots':deleted,'requires_operator_review':issues,'limitations':['Incomplete/untrusted snapshots are preserved for safe operator cleanup; their presence never blocks authenticated expiry of other snapshots.','This check enforces configured expiry; it does not prove elapsed 30-day retention or independent replication.']}
        target=ROOT/'verification/reports/backup-retention.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2)+'\n')
    return deleted


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['snapshot','expire']);args=parser.parse_args()
    if args.command=='snapshot':print('Encrypted snapshot created:',snapshot().name)
    else:print('Expired encrypted snapshots removed:',expire())
