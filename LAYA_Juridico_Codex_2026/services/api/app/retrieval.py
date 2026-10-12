import re
from datetime import date
from langchain_core.runnables import RunnableLambda
from .contracts import Candidate
from .errors import DomainError
from .fusion import fuse
from psycopg.errors import QueryCanceled
from psycopg import OperationalError

BASE="""SELECT c.id candidate_id,i.id instrument_id,v.id section_version_id,
 i.title||' · '||s.heading heading,c.passage,v.language_code,i.jurisdiction_id jurisdiction_code,
 i.official_reference,coalesce(v.official_url,i.official_url) official_url,v.publication_date,v.effective_from,v.effective_to,
 v.effectiveness_verified,p.source_id,c.start_offset,c.end_offset,v.version_ref,v.consolidation_date,p.is_consolidated,i.ingestion_warnings
 FROM legal.chunks c JOIN legal.section_versions v ON v.id=c.version_id
 JOIN legal.sections s ON s.id=v.section_id JOIN legal.instruments i ON i.id=s.instrument_id
 JOIN legal.publications p ON p.id=v.publication_id WHERE """


class CandidateBatch(list):
    def __init__(self,values,embedding_degraded,retrieval_warnings=None):
        super().__init__(values)
        self.embedding_degraded=embedding_degraded
        self.retrieval_warnings=retrieval_warnings or []


def version_filters(request, *, current_cache=False):
    cutoff=request.as_of or date.today()
    filters=["v.publication_date<=%s"]
    params=[cutoff]
    if request.verified_only:
        filters += ["v.effectiveness_verified","v.effective_from<=%s","(v.effective_to IS NULL OR v.effective_to>%s)"]
        params += [cutoff]*2
    if not request.include_historical:
        qualifying=" AND ".join(filters).replace("v.","")
        selector="SELECT DISTINCT ON(section_id) id FROM legal.section_versions WHERE "+qualifying+" ORDER BY section_id,consolidation_date DESC NULLS LAST,source_order DESC,id DESC"
        if current_cache and request.as_of is None and not request.verified_only:
            filters.append('v.id IN (SELECT version_id FROM legal.current_versions_cache)')
        else:
            filters.append('v.id IN ('+selector+')')
            params += params.copy()
    return filters,params


class HybridRetriever:
    def __init__(self,db,embedding_client):
        self.db,self.embeddings=db,embedding_client
        self.sql_timeout_seconds=getattr(getattr(embedding_client,'settings',None),'search_sql_timeout_seconds',30)
        self.runnable=RunnableLambda(self._retrieve)

    async def ainvoke(self,query):
        return await self.runnable.ainvoke(query,config={"callbacks":[]})

    async def _retrieve(self,query):
        if len(query.retrieval_inputs)<=1:return await self._retrieve_single(query)
        batches=[]
        for index,text in enumerate(query.retrieval_inputs[:4]):
            batch=await self._retrieve_single(query.model_copy(update={"query":text,"retrieval_inputs":[]}))
            for candidate in batch:
                for signal in candidate.retrieval_evidence:
                    signal['input_index']=index
                    if index<len(query.retrieval_sources):signal.update(query.retrieval_sources[index])
            batches.append(batch)
        items={}
        for batch in batches:
            for candidate in batch:
                if candidate.candidate_id in items:items[candidate.candidate_id].retrieval_evidence.extend(candidate.retrieval_evidence)
                else:items[candidate.candidate_id]=candidate
        ranks=fuse([[c.candidate_id for c in batch] for batch in batches])
        return CandidateBatch([items[key].model_copy(update={"score":score}) for key,score in ranks[:50]],any(b.embedding_degraded for b in batches),list(dict.fromkeys(w for b in batches for w in b.retrieval_warnings)))

    async def _retrieve_single(self,query):
        request=query.request
        retrieval_warnings=[]
        async with self.db.tenant_transaction(query.context) as conn:
            await conn.execute("SELECT set_config('statement_timeout',%s,true)",(str(self.sql_timeout_seconds*1000)+'ms',))
            # Selectivity varies sharply by query/date/territory. A pooled generic
            # prepared plan can scan the entire corpus instead of the FTS index.
            await conn.execute("SET LOCAL plan_cache_mode='force_custom_plan'")
            cache=await (await conn.execute('SELECT as_of FROM legal.current_cache_metadata WHERE singleton')).fetchone()
            filters,params=version_filters(request,current_cache=bool(cache and cache['as_of']==date.today()))
            if request.legal_types:
                filters.append('i.legal_type=ANY(%s)');params.append(request.legal_types)
            if request.territory_codes:
                rows=await (await conn.execute("SELECT id FROM legal.jurisdictions WHERE id=ANY(%s)",(request.territory_codes,))).fetchall()
                if len(rows)!=len(set(request.territory_codes)):
                    raise DomainError("TERRITORY_UNKNOWN",422)
                filters.append("i.jurisdiction_id IN (WITH RECURSIVE tree AS (SELECT id FROM legal.jurisdictions WHERE id=ANY(%s) UNION ALL SELECT j.id FROM legal.jurisdictions j JOIN tree t ON j.parent_id=t.id), ancestors AS (SELECT id,parent_id FROM legal.jurisdictions WHERE id=ANY(%s) UNION ALL SELECT j.id,j.parent_id FROM legal.jurisdictions j JOIN ancestors a ON j.id=a.parent_id) SELECT id FROM tree UNION SELECT id FROM ancestors)")
                params.extend([request.territory_codes,request.territory_codes])
            where=" AND ".join(filters)
            results=[]
            engines=[]
            async def rows_for(sql,values):
                try:
                    async with conn.transaction():return await (await conn.execute(sql,values)).fetchall()
                except QueryCanceled:
                    if 'TEXT_RETRIEVAL_DEGRADED' not in retrieval_warnings:retrieval_warnings.append('TEXT_RETRIEVAL_DEGRADED')
                    return []
            identifiers=re.findall(r"BOE-A-\d{4}-\d+|\b\d+/\d{4}\b",query.query,re.IGNORECASE)
            if identifiers:
                rows=await rows_for(BASE+where+" AND (i.id=ANY(%s) OR i.official_reference=ANY(%s)) ORDER BY c.id LIMIT 100",params+[identifiers,identifiers])
                results.append(rows);engines.append("exact_reference")
            fts=await rows_for(BASE+where+" AND c.search_vector @@ websearch_to_tsquery('simple',public.unaccent(%s)) ORDER BY ts_rank_cd(c.search_vector,websearch_to_tsquery('simple',public.unaccent(%s))) DESC,c.id LIMIT 100",params+[query.query,query.query])
            results.append(fts);engines.append("lexical")
            terms=re.findall(r"[^\W_]+",query.query,flags=re.UNICODE)
            sparse=" OR ".join(t for t in terms if len(t)>3)[:3000]
            if sparse:
                broad=await rows_for(BASE+where+" AND c.search_vector @@ websearch_to_tsquery('simple',public.unaccent(%s)) ORDER BY ts_rank_cd(c.search_vector,websearch_to_tsquery('simple',public.unaccent(%s))) DESC,c.id LIMIT 100",params+[sparse,sparse])
                results.append(broad);engines.append("lexical_broad")
            trigram=await rows_for(BASE+where+" AND i.title %% %s ORDER BY similarity(i.title,%s) DESC,c.id LIMIT 50",params+[query.query,query.query])
            results.append(trigram);engines.append("title_similarity")
        embedding_degraded=False
        try:
            vector=(await self.embeddings.embed([query.query]))[0]
            from pgvector import Vector
            # Filters apply inside the vector query, before LIMIT. Exact distance on small filtered corpora.
            async with self.db.tenant_transaction(query.context) as conn:
                from pgvector.psycopg import register_vector_async
                await register_vector_async(conn)
                await conn.execute("SELECT set_config('statement_timeout',%s,true)",(str(self.sql_timeout_seconds*1000)+'ms',))
                await conn.execute("SET LOCAL plan_cache_mode='force_custom_plan'")
                semantic=await (await conn.execute(BASE+where+" AND c.embedding IS NOT NULL AND c.embedding_revision=%s ORDER BY c.embedding <=> %s,c.id LIMIT 100",params+[self.embeddings.settings.embedding_model_revision,Vector(vector)])).fetchall()
                results.append(semantic);engines.append("semantic")
        except (RuntimeError,ImportError,OSError,ValueError,QueryCanceled,OperationalError):
            embedding_degraded=True
        if request.scope=='all_publications':
            try:
                from .bulletin_retrieval import retrieve_bulletins
                bulletin=await retrieve_bulletins(self,query)
                if bulletin:
                    results.append([c.model_dump(exclude={'score','retrieval_evidence'})|{'retrieval_evidence':c.retrieval_evidence,'ingestion_warnings':c.ingestion_warnings} for c in bulletin]);engines.append('bulletin_hybrid')
                retrieval_warnings.append('BULLETIN_INDEX_PARTIAL')
            except (QueryCanceled,OperationalError,RuntimeError):retrieval_warnings.append('BULLETIN_RETRIEVAL_DEGRADED')
        items={row["candidate_id"]:row for rows in results for row in rows}
        ranking=fuse([[row["candidate_id"] for row in rows] for rows in results])
        selected=[]
        per_version={}
        for identifier,score in ranking:
            row=items[identifier]
            version=row["section_version_id"]
            if per_version.get(version,0)>=2:continue
            per_version[version]=per_version.get(version,0)+1
            evidence=[{"engine":engine,"rank":rank+1,"rrf_contribution":1/(61+rank)} for engine,rows in zip(engines,results) for rank,item in enumerate(rows) if item["candidate_id"]==identifier]
            selected.append(Candidate(**{k:v for k,v in row.items() if k not in {"retrieval_evidence","validity_status"}},retrieval_evidence=row.get("retrieval_evidence",[])+evidence,score=score,validity_status="verified_interval" if row["effectiveness_verified"] else "unknown"))
            if len(selected)==50:break
        return CandidateBatch(selected,embedding_degraded,retrieval_warnings)
