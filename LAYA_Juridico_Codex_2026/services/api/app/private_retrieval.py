"""Isolated literal passage retrieval; selected document IDs are never authorization."""
from langchain_core.runnables import RunnableLambda
from pgvector import Vector
from pgvector.psycopg import register_vector_async
from .errors import DomainError
from .fusion import fuse
from .query_intent import split_passages

class PrivateRetriever:
    def __init__(self,db,embeddings):self.db,self.embeddings=db,embeddings;self.runnable=RunnableLambda(self._retrieve)
    async def ainvoke(self,query):return await self.runnable.ainvoke(query,config={'callbacks':[]})
    async def authorize(self,context,ids):
        async with self.db.tenant_transaction(context) as conn:
            rows=await (await conn.execute("SELECT id,filename,parse_status,deletion_epoch FROM private.documents WHERE id=ANY(%s) AND deleted_at IS NULL AND trashed_at IS NULL",(ids,))).fetchall()
            if len(rows)!=len(ids):raise DomainError('ATTACHMENT_NOT_AVAILABLE',404)
            if any(r['parse_status']!='ready' for r in rows):raise DomainError('ATTACHMENT_NOT_READY',409)
            return rows
    async def _retrieve(self,query):
        context,ids,text=query['context'],query['ids'],query['query']
        docs=await self.authorize(context,ids);epochs={str(r['id']):r['deletion_epoch'] for r in docs}
        warnings=[];lists=[];items={}
        async with self.db.tenant_transaction(context) as conn:
            rows=await (await conn.execute('''SELECT p.*,d.filename,ts_rank_cd(p.search_vector,plainto_tsquery('simple',public.unaccent(%s))) lexical_score
             FROM private.passage_index p JOIN private.documents d ON d.id=p.document_id WHERE p.document_id=ANY(%s)
             AND d.deleted_at IS NULL AND d.trashed_at IS NULL ORDER BY lexical_score DESC,p.id LIMIT 100''',(text,ids))).fetchall()
            lists.append([r['id'] for r in rows if r['lexical_score']>0]);items.update({r['id']:r for r in rows})
            indexed=await (await conn.execute('SELECT DISTINCT document_id FROM private.passage_index WHERE document_id=ANY(%s)',(ids,))).fetchall()
            missing=set(ids)-{r['document_id'] for r in indexed}
            if missing:
                # Real extraction is already durable; lexical fallback until indexing completes.
                warnings.append('PRIVATE_INDEX_PENDING')
                pages=await (await conn.execute('''SELECT c.*,d.filename FROM private.chunks c JOIN private.documents d ON d.id=c.document_id
                 WHERE c.document_id=ANY(%s) AND d.deleted_at IS NULL AND d.trashed_at IS NULL ORDER BY c.document_id,c.page_number''',(list(missing),))).fetchall()
                terms=set(text.casefold().split())
                fallback=[]
                for page in pages:
                    for start,end,passage in split_passages(page['text']):
                        key=f"{page['document_id']}:{page['page_number']}:{start}"
                        row={**page,'id':key,'start_offset':start,'end_offset':end,'passage':passage}
                        score=sum(term in passage.casefold() for term in terms if len(term)>2)
                        if score:fallback.append((score,key,row))
                fallback.sort(key=lambda r:(-r[0],r[1]))
                lists.append([r[1] for r in fallback[:100]]);items.update({r[1]:r[2] for r in fallback[:100]})
        try:
            vector=(await self.embeddings.embed([text]))[0]
            async with self.db.tenant_transaction(context) as conn:
                await register_vector_async(conn)
                rows=await (await conn.execute('''SELECT p.*,d.filename FROM private.passage_index p JOIN private.documents d ON d.id=p.document_id
                  WHERE p.document_id=ANY(%s) AND d.deleted_at IS NULL AND d.trashed_at IS NULL AND p.embedding_revision=%s
                  ORDER BY p.embedding <=> %s,p.id LIMIT 100''',(ids,self.embeddings.settings.embedding_model_revision,Vector(vector)))).fetchall()
                lists.append([r['id'] for r in rows]);items.update({r['id']:r for r in rows})
        except (RuntimeError,OSError,ValueError):warnings.append('EMBEDDINGS_UNAVAILABLE')
        output=[]
        for key,score in fuse(lists)[:50]:
            r=items[key]
            evidence=[{'engine':'private_lexical' if i<len(lists)-1 or 'EMBEDDINGS_UNAVAILABLE' in warnings else 'private_semantic','rank':ranks.index(key)+1} for i,ranks in enumerate(lists) if key in ranks]
            output.append({k:r[k] for k in ('document_id','filename','page_number','start_offset','end_offset','passage','ocr_uncertain')})
            output[-1].update(candidate_id=key,score=score,retrieval_evidence=evidence)
        latest=await self.authorize(context,ids)
        if any(epochs[str(r['id'])]!=r['deletion_epoch'] for r in latest):raise DomainError('ATTACHMENT_NOT_AVAILABLE',404)
        return {'results':output,'warnings':warnings}
