from uuid import uuid4
import pytest
import psycopg
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.contracts import TenantContext
from services.api.app.errors import DomainError


@pytest.fixture
def tenants():
    settings=Settings()
    if not settings.admin_database_url: pytest.skip("Configured PostgreSQL required; skip cannot pass release")
    user=uuid4(); a=uuid4(); b=uuid4()
    with psycopg.connect(settings.admin_database_url) as conn:
        conn.execute("INSERT INTO private.tenants VALUES(%s,'Synthetic test A'),(%s,'Synthetic test B')",(a,b))
        conn.execute("INSERT INTO private.tenant_members VALUES(%s,%s,'lawyer'),(%s,%s,'lawyer')",(a,user,b,user))
        for tenant in (a,b):
            conn.execute("INSERT INTO private.documents(id,tenant_id,uploader,filename,mime_type,object_key,sha256,idempotency_key) VALUES(%s,%s,%s,'synthetic','application/pdf','synthetic','hash',%s)",(uuid4(),tenant,user,str(uuid4())))
    yield settings,user,a,b
    with psycopg.connect(settings.admin_database_url) as conn:
        conn.execute("DELETE FROM private.chunks WHERE tenant_id=ANY(%s)",([a,b],))
        conn.execute("DELETE FROM private.documents WHERE tenant_id=ANY(%s)",([a,b],))
        conn.execute("DELETE FROM private.tenant_members WHERE tenant_id=ANY(%s)",([a,b],))
        conn.execute("DELETE FROM private.tenants WHERE id=ANY(%s)",([a,b],))


@pytest.mark.database
async def test_active_tenant_multi_membership_and_pool_reset(tenants):
    settings,user,a,b=tenants
    db=Database(settings.database_url)
    await db.open()
    for active in (a,b,a):
        context=TenantContext(user_id=user,tenant_id=active,role="lawyer")
        async with db.tenant_transaction(context) as conn:
            rows=await (await conn.execute("SELECT tenant_id FROM private.documents")).fetchall()
            assert rows and all(row["tenant_id"]==active for row in rows)
    async with db.pool.connection() as conn:
        assert await (await conn.execute("SELECT id FROM private.documents")).fetchall()==[]
    with pytest.raises(DomainError):
        async with db.tenant_transaction(TenantContext(user_id=uuid4(),tenant_id=a,role="lawyer")):pass
    await db.close()


@pytest.mark.database
def test_cross_tenant_chunk_parent_rejected(tenants):
    settings,user,a,b=tenants
    with psycopg.connect(settings.admin_database_url) as conn:
        doc=conn.execute("SELECT id FROM private.documents WHERE tenant_id=%s",(a,)).fetchone()[0]
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                conn.execute("INSERT INTO private.chunks VALUES(%s,%s,1,'synthetic',false)",(doc,b))
