from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from .contracts import TenantContext
from .errors import DomainError


class Database:
    def __init__(self, url: str, *, worker: bool = False):
        self.pool = AsyncConnectionPool(url, open=False, min_size=1, max_size=8,
                                        kwargs={"row_factory": dict_row}, timeout=5)
        self.worker = worker

    async def open(self):
        await self.pool.open()
        await self.pool.wait(timeout=10)
        async with self.pool.connection() as conn:
            row = await (await conn.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")).fetchone()
            if row["rolsuper"] or row["rolbypassrls"]:
                raise RuntimeError("User database role must not bypass RLS")

    async def close(self):
        await self.pool.close()

    @asynccontextmanager
    async def tenant_transaction(self, context: TenantContext):
        async with self.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.user_id',%s,true),set_config('app.tenant_id',%s,true)",
                                   (str(context.user_id), str(context.tenant_id)))
                if not self.worker:
                    row = await (await conn.execute("SELECT private.member_role(%s) AS role", (context.tenant_id,))).fetchone()
                    if not row or row["role"] != context.role:
                        raise DomainError("TENANT_FORBIDDEN", 403)
                yield conn

    async def resolve_membership(self, user_id, tenant_id):
        async with self.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.user_id',%s,true)", (str(user_id),))
                row = await (await conn.execute("SELECT private.member_role(%s) AS role", (tenant_id,))).fetchone()
                return row["role"] if row else None
