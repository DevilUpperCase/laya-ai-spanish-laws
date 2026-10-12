from uuid import uuid4
import psycopg
import pytest
from services.api.app.config import Settings


def test_last_crashed_extraction_is_terminal_and_api_cannot_recover_jobs():
    settings=Settings();tenant=uuid4();document=uuid4();user=uuid4()
    with psycopg.connect(settings.admin_database_url) as admin:
        admin.execute('INSERT INTO private.tenants(id,name) VALUES(%s,%s)',(tenant,'Recovery regression'))
        admin.execute("INSERT INTO private.documents(id,tenant_id,uploader,filename,mime_type,object_key,sha256,idempotency_key) VALUES(%s,%s,%s,'synthetic','application/pdf','synthetic','synthetic','lease-test')",(document,tenant,user))
        admin.execute("INSERT INTO private.jobs(document_id,tenant_id,kind,status,attempts,lease_until,deletion_epoch) VALUES(%s,%s,'extract','processing',5,now()-interval '1 minute',0)",(document,tenant));admin.commit()
        try:
            with psycopg.connect(settings.worker_database_url) as worker:
                worker.execute('SELECT private.recover_exhausted_jobs()');worker.commit()
            assert admin.execute('SELECT parse_status,failure_code FROM private.documents WHERE id=%s',(document,)).fetchone()==('failed','LEASE_EXHAUSTED')
            assert admin.execute('SELECT status FROM private.jobs WHERE document_id=%s',(document,)).fetchone()[0]=='failed'
            with psycopg.connect(settings.database_url) as api:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):api.execute('SELECT private.recover_exhausted_jobs()')
        finally:
            admin.rollback();admin.execute('DELETE FROM private.jobs WHERE document_id=%s',(document,));admin.execute('DELETE FROM private.documents WHERE id=%s',(document,));admin.execute('DELETE FROM private.tenants WHERE id=%s',(tenant,));admin.commit()
