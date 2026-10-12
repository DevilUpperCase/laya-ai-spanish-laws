from datetime import date
from uuid import uuid4
import psycopg
import pytest
from services.api.app.config import Settings
from services.api.app.contracts import SearchRequest
from services.api.app.retrieval import version_filters
from scripts.reapply_deletions import reapply
from tests.integration.test_isolation import tenants


@pytest.mark.database
def test_future_published_amendment_does_not_hide_effective_version():
    settings=Settings()
    with psycopg.connect(settings.admin_database_url) as conn:
        for verified,expected in ((True,"old"),(False,"future")):
            clauses,params=version_filters(SearchRequest(query="test",as_of=date(2026,6,1),verified_only=verified))
            sql="""WITH versions(id,section_id,publication_date,consolidation_date,source_order,effectiveness_verified,effective_from,effective_to) AS (VALUES
             ('old','one',date '2025-01-01',date '2025-01-01',0,true,date '2025-01-01',date '2026-07-01'),
             ('future','one',date '2026-05-01',date '2026-05-01',1,true,date '2026-07-01',NULL))
             SELECT v.id FROM versions v WHERE """+" AND ".join(clauses).replace("legal.section_versions","versions")
            assert conn.execute(sql,params).fetchall()==[(expected,)]


@pytest.mark.database
def test_restore_replay_is_idempotent_with_completed_purge(tenants):
    settings,user,a,b=tenants
    try:
        with psycopg.connect(settings.admin_database_url) as conn:
            doc=conn.execute("SELECT id FROM private.documents WHERE tenant_id=%s",(a,)).fetchone()[0]
            conn.execute("INSERT INTO private.jobs(document_id,tenant_id,kind,deletion_epoch,status) VALUES(%s,%s,'purge',1,'complete')",(doc,a))
            records=[{"tenant_id":str(a),"document_id":str(doc),"epoch":1,"deleted_at":"2026-01-01T00:00:00+00:00"}]
            reapply(conn,records)
            reapply(conn,records)
            assert conn.execute("SELECT status FROM private.jobs WHERE document_id=%s",(doc,)).fetchone()[0]=="queued"
            assert conn.execute("SELECT count(*) FROM private.deletion_records WHERE document_id=%s",(doc,)).fetchone()[0]==1
    finally:
        with psycopg.connect(settings.admin_database_url) as conn:
            conn.execute("DELETE FROM private.jobs WHERE tenant_id=ANY(%s)",([a,b],))
            conn.execute("DELETE FROM private.deletion_records WHERE tenant_id=ANY(%s)",([a,b],))
