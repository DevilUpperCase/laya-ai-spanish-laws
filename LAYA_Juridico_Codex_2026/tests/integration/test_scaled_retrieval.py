import psycopg
from services.api.app.config import Settings
from services.api.app.contracts import SearchRequest
from services.api.app.retrieval import BASE,version_filters
from psycopg.rows import dict_row
import json
from pathlib import Path
from uuid import UUID
import pytest
from services.api.app.config import ROOT
from services.api.app.database import Database
from services.api.app.contracts import RetrievalQuery,TenantContext
from services.api.app.retrieval import HybridRetriever


def test_title_retrieval_with_full_boe_corpus_meets_internal_sql_budget():
    settings=Settings()
    with psycopg.connect(settings.database_url,row_factory=dict_row) as conn:
        conn.execute("SET statement_timeout='5s'")
        filters,params=version_filters(SearchRequest(query='arrendamiento vivienda'))
        rows=conn.execute(BASE+' AND '.join(filters)+' AND i.title %% %s ORDER BY similarity(i.title,%s) DESC,c.id LIMIT 50',params+['arrendamiento vivienda']*2).fetchall()
        assert isinstance(rows,list)


@pytest.mark.database
@pytest.mark.parametrize('text',['arrendamiento vivienda','vivienda'])
async def test_pooled_generic_plan_does_not_break_text_baseline(text):
    class UnavailableEmbeddings:
        async def embed(self,texts):raise RuntimeError('Unavailable for baseline check')
    settings=Settings();local=json.loads((ROOT/'private-data/local-session.json').read_text())
    db=Database(settings.database_url);await db.open()
    try:
        user=UUID(local['user_id']);tenant=UUID(local['tenant_id']);role=await db.resolve_membership(user,tenant)
        async with db.pool.connection() as conn:await conn.execute("SET plan_cache_mode='force_generic_plan'")
        query=RetrievalQuery(query=text,request=SearchRequest(query=text),context=TenantContext(user_id=user,tenant_id=tenant,role=role),trace_id='scaled-baseline')
        result=await HybridRetriever(db,UnavailableEmbeddings()).ainvoke(query)
        assert result and result.embedding_degraded
    finally:await db.close()
