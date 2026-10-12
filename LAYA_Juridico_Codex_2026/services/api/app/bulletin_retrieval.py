"""Original bulletin recall, distinct from normative instrument/version retrieval."""
from datetime import date
from pgvector import Vector
from pgvector.psycopg import register_vector_async
from .contracts import Candidate
from .fusion import fuse

async def retrieve_bulletins(retriever,query):
    request=query.request;params=[request.as_of or date.today()];filters=["i.status='complete'","i.publication_date<=%s"]
    if request.scope=='normative':filters.append('i.normative')
    if request.verified_only:return [] # Original notices have no audited effectiveness intervals.
    if request.legal_types:return [] # No unaudited mapping from bulletin category to legal type.
    if request.territory_codes:
        # BOE/BORME are state publications; territorial applicability is not inferred.
        # Include the state ancestor for a selected municipality/region.
        filters.append("i.jurisdiction_id IN (WITH RECURSIVE tree AS (SELECT id FROM legal.jurisdictions WHERE id=ANY(%s) UNION ALL SELECT j.id FROM legal.jurisdictions j JOIN tree t ON j.parent_id=t.id), a AS (SELECT id,parent_id FROM legal.jurisdictions WHERE id=ANY(%s) UNION ALL SELECT j.id,j.parent_id FROM legal.jurisdictions j JOIN a ON j.id=a.parent_id) SELECT id FROM tree UNION SELECT id FROM a)")
        params.extend([request.territory_codes,request.territory_codes])
    where=' AND '.join(filters);base='SELECT c.*,i.title,i.external_id,i.official_url,i.publication_date,i.category,i.normative,i.source_id,i.jurisdiction_id FROM legal.bulletin_chunks c JOIN legal.bulletin_items i ON i.id=c.item_id WHERE '+where
    lists=[];engines=[]
    async with retriever.db.tenant_transaction(query.context) as conn:
        await conn.execute("SELECT set_config('statement_timeout',%s,true)",(str(retriever.sql_timeout_seconds*1000)+'ms',))
        # Exact IDs are matched against the literal query without treating an arbitrary query as SQL syntax.
        import re
        identifiers=re.findall(r'(?:BOE|BORME)-[AB]-\d{4}-[\d-]+',query.query,re.I)
        if identifiers:
            exact=await (await conn.execute(base+' AND i.external_id=ANY(%s) ORDER BY c.id LIMIT 100',params+[identifiers])).fetchall()
            lists.append(exact);engines.append('exact_reference')
        rows=await (await conn.execute(base+" AND c.search_vector @@ plainto_tsquery('simple',public.unaccent(%s)) ORDER BY ts_rank_cd(c.search_vector,plainto_tsquery('simple',public.unaccent(%s))) DESC,c.id LIMIT 100",params+[query.query,query.query])).fetchall()
        lists.append(rows);engines.append('lexical')
    try:
        vector=(await retriever.embeddings.embed([query.query]))[0]
        async with retriever.db.tenant_transaction(query.context) as conn:
            await register_vector_async(conn)
            await conn.execute("SELECT set_config('statement_timeout',%s,true)",(str(retriever.sql_timeout_seconds*1000)+'ms',))
            rows=await (await conn.execute(base+' AND c.embedding_revision=%s ORDER BY c.embedding <=> %s,c.id LIMIT 100',params+[retriever.embeddings.settings.embedding_model_revision,Vector(vector)])).fetchall()
            lists.append(rows);engines.append('semantic')
    except (RuntimeError,OSError,ValueError):pass
    items={r['id']:r for rows in lists for r in rows};results=[]
    for key,score in fuse([[r['id'] for r in rows] for rows in lists])[:50]:
        r=items[key];evidence=[{'engine':engine,'rank':rank+1,'rrf_contribution':1/(61+rank)} for engine,rows in zip(engines,lists) for rank,item in enumerate(rows) if item['id']==key]
        results.append(Candidate(candidate_id=key,instrument_id='bulletin:'+r['item_id'],section_version_id='bulletin:'+r['item_id'],heading=r['title']+' · '+r['category'],passage=r['passage'],language_code='es',jurisdiction_code=r['jurisdiction_id'],official_reference=r['external_id'],official_url=r['official_url'],publication_date=r['publication_date'],source_id=r['source_id'],start_offset=r['start_offset'],end_offset=r['end_offset'],version_ref=r['external_id'],is_consolidated=False,retrieval_evidence=evidence,score=score,ingestion_warnings=[] if r['normative'] else ['INDIVIDUAL_PUBLICATION_NOT_GENERAL_RULE']))
    return results
