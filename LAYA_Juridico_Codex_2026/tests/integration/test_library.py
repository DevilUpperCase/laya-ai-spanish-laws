from uuid import uuid4
import psycopg
import pytest
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.contracts import TenantContext
from services.api.app.library import LibraryService
from services.api.app.errors import DomainError


@pytest.mark.database
async def test_library_tenant_roles_and_revision_conflicts(tmp_path):
    settings=Settings(private_storage_path=tmp_path)
    a,b,user=uuid4(),uuid4(),uuid4()
    with psycopg.connect(settings.admin_database_url) as conn:
        conn.execute("INSERT INTO private.tenants VALUES(%s,'Library test'),(%s,'Foreign test')",(a,b))
        conn.execute("INSERT INTO private.tenant_members VALUES(%s,%s,'admin')",(a,user))
    db=Database(settings.database_url);await db.open()
    lib=LibraryService(db,settings);ctx=TenantContext(user_id=user,tenant_id=a,role='admin')
    try:
        folder=await lib.create_folder(ctx,'Case A',None)
        with pytest.raises(DomainError):await lib.move_folder(ctx,folder['id'],folder['id'])
        notebook=await lib.create_notebook(ctx,'Research',folder['id'])
        note=await lib.save_note(ctx,{'notebook_id':notebook['id'],'body':'Human-written evidence'})
        await lib.save_note(ctx,{'body':'Edited','revision':1},note['id'])
        with pytest.raises(DomainError) as error:await lib.save_note(ctx,{'body':'Lost edit','revision':1},note['id'])
        assert error.value.status==409
        reader=TenantContext(user_id=user,tenant_id=a,role='reader')
        with pytest.raises(DomainError):await lib.create_folder(reader,'No',None)
        foreign=TenantContext(user_id=user,tenant_id=b,role='admin')
        with pytest.raises(DomainError):await lib.get_notebook(foreign,notebook['id'])
    finally:
        await db.close()
        with psycopg.connect(settings.admin_database_url) as conn:
            for table in ('notes','saved_references','notebooks','folders','tenant_members'):
                conn.execute(f'DELETE FROM private.{table} WHERE tenant_id=ANY(%s)',([a,b],))
            conn.execute('DELETE FROM private.tenants WHERE id=ANY(%s)',([a,b],))


@pytest.mark.database
async def test_trash_restore_and_permanent_delete(tmp_path):
    from io import BytesIO
    from starlette.datastructures import UploadFile,Headers
    from services.api.app.documents import DocumentService
    from services.api.app.jobs import JobWorker
    from scripts.reapply_deletions import reapply
    from services.api.app.deletion_journal import read_journal
    import pymupdf
    settings=Settings(private_storage_path=tmp_path/'objects',deletion_journal_path=tmp_path/'journal.jsonl')
    a,user=uuid4(),uuid4()
    with psycopg.connect(settings.admin_database_url) as conn:
        conn.execute("INSERT INTO private.tenants VALUES(%s,'Trash test')",(a,))
        conn.execute("INSERT INTO private.tenant_members VALUES(%s,%s,'admin')",(a,user))
    db=Database(settings.database_url);worker_db=Database(settings.worker_database_url,worker=True)
    await db.open();await worker_db.open()
    lib=LibraryService(db,settings);docs=DocumentService(db,settings);ctx=TenantContext(user_id=user,tenant_id=a,role='admin')
    try:
        pdf=pymupdf.open();pdf.new_page().insert_text((50,50),'Synthetic notebook original')
        doc=await docs.upload(ctx,UploadFile(BytesIO(pdf.tobytes()),filename='original.pdf',headers=Headers({'content-type':'application/pdf'})),'trash-test')
        worker=JobWorker(worker_db,settings);assert await worker.run_once(doc.id)
        notebook=await lib.create_notebook(ctx,'Notes')
        await lib.save_note(ctx,{'notebook_id':notebook['id'],'document_id':doc.id,'body':'Linked note'})
        await lib.save_note(ctx,{'notebook_id':notebook['id'],'body':'General note'})
        await lib.update_document(ctx,doc.id,trash=True)
        assert not (await lib.list_documents(ctx))['items']
        assert (await lib.list_documents(ctx,trash=True))['items'][0]['id']==doc.id
        with pytest.raises(DomainError):await docs.get(ctx,doc.id)
        assert (await docs.get(ctx,doc.id,trash=True)).pages
        assert len((await lib.get_notebook(ctx,notebook['id']))['notes'])==1
        assert len(await lib.trash_notes(ctx,doc.id))==1
        await lib.update_document(ctx,doc.id,trash=False)
        assert len((await lib.get_notebook(ctx,notebook['id']))['notes'])==2
        await docs.delete(ctx,doc.id)
        with pytest.raises(DomainError):await lib.update_document(ctx,doc.id,trash=False)
        assert len((await lib.get_notebook(ctx,notebook['id']))['notes'])==1
        with psycopg.connect(settings.admin_database_url) as conn:reapply(conn,read_journal(settings.deletion_journal_path))
        assert await worker.run_once(doc.id)
        with psycopg.connect(settings.admin_database_url) as conn:
            assert conn.execute('SELECT count(*) FROM private.notes WHERE document_id=%s',(doc.id,)).fetchone()[0]==0
        assert not list(settings.private_storage_path.rglob('original'))
    finally:
        await db.close();await worker_db.close()
        with psycopg.connect(settings.admin_database_url) as conn:
            for table in ('notes','saved_references','notebooks','folders','jobs','passage_index','chunks','deletion_records','documents','tenant_members'):
                conn.execute(f'DELETE FROM private.{table} WHERE tenant_id=%s',(a,))
            conn.execute('DELETE FROM private.tenants WHERE id=%s',(a,))
