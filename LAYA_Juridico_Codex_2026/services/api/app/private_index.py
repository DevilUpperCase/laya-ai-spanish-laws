"""Small durable indexing batches; deletion and lease checked before commit."""
import hashlib
from pgvector import Vector
from pgvector.psycopg import register_vector_async
from .query_intent import split_passages

async def index_batch(worker,context,job):
    async with worker.db.tenant_transaction(context) as conn:
        pages=await (await conn.execute('SELECT * FROM private.chunks WHERE document_id=%s ORDER BY page_number',(job['document_id'],))).fetchall()
        existing=await (await conn.execute('SELECT id FROM private.passage_index WHERE document_id=%s AND embedding_revision=%s',(job['document_id'],worker.settings.embedding_model_revision))).fetchall()
    known={r['id'] for r in existing};pending=[]
    for page in pages:
        for start,end,passage in split_passages(page['text']):
            key=hashlib.sha256((str(job['document_id'])+':'+str(page['page_number'])+':'+str(start)+':'+passage).encode()).hexdigest()
            if key not in known:pending.append((key,page['page_number'],start,end,passage,page['ocr_uncertain']))
    batch=pending[:8]
    vectors=await worker.embeddings.embed([r[4] for r in batch]) if batch else []
    async with worker.db.tenant_transaction(context) as conn:
        doc=await (await conn.execute('SELECT * FROM private.documents WHERE id=%s FOR UPDATE',(job['document_id'],))).fetchone()
        lease=await (await conn.execute('SELECT * FROM private.jobs WHERE id=%s FOR UPDATE',(job['id'],))).fetchone()
        if not doc or doc['deleted_at'] or doc['deletion_epoch']!=job['deletion_epoch'] or lease['lease_token']!=job['lease_token'] or lease['status']!='processing':return
        await register_vector_async(conn)
        for r,vector in zip(batch,vectors):
            await conn.execute('''INSERT INTO private.passage_index(id,document_id,tenant_id,page_number,start_offset,end_offset,passage,ocr_uncertain,search_vector,embedding,embedding_revision)
             VALUES(%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple',public.unaccent(%s)),%s,%s)
             ON CONFLICT(id) DO UPDATE SET embedding=EXCLUDED.embedding,embedding_revision=EXCLUDED.embedding_revision''',
             (r[0],doc['id'],doc['tenant_id'],r[1],r[2],r[3],r[4],r[5],r[4],Vector(vector),worker.settings.embedding_model_revision))
        if len(pending)>len(batch):
            await conn.execute("UPDATE private.jobs SET status='retry',attempts=0,next_attempt=now(),lease_until=NULL,lease_token=NULL WHERE id=%s",(job['id'],))
        else:await worker._finish(conn,job,'complete')
