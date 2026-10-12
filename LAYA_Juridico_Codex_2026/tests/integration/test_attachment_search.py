from types import SimpleNamespace
from uuid import uuid4
import hashlib
import pytest,psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.contracts import TenantContext
from services.api.app.private_retrieval import PrivateRetriever
from services.api.app.errors import DomainError
from services.api.app.query_intent import split_passages

class FixedVectors:
    settings=SimpleNamespace(embedding_model_revision='mechanical-test-only')
    async def embed(self,texts):return [[1.0]+[0.0]*1023 for _ in texts]

@pytest.mark.database
async def test_two_attachments_semantic_evidence_and_trash_isolation():
    settings=Settings();tenant,user=uuid4(),uuid4();docs=[uuid4(),uuid4()]
    with psycopg.connect(settings.admin_database_url) as conn:
        register_vector(conn)
        conn.execute("INSERT INTO private.tenants VALUES(%s,'Attachment mechanics')",(tenant,))
        conn.execute("INSERT INTO private.tenant_members VALUES(%s,%s,'admin')",(tenant,user))
        for i,doc in enumerate(docs):
            conn.execute("INSERT INTO private.documents(id,tenant_id,uploader,filename,mime_type,object_key,sha256,idempotency_key,parse_status) VALUES(%s,%s,%s,%s,'application/pdf','synthetic','test',%s,'ready')",(doc,tenant,user,'Case '+str(i),str(doc)))
            text='Arrendamiento de vivienda sin coincidencia literal con shelter'
            conn.execute("INSERT INTO private.passage_index VALUES(%s,%s,%s,1,0,%s,%s,false,to_tsvector('simple',%s),%s,'mechanical-test-only')",(str(doc),doc,tenant,len(text),text,text,Vector([1.0]+[0.0]*1023)))
        long_text=('tenant protections vivienda y arrendamiento. '*48)
        conn.execute('INSERT INTO private.chunks(document_id,tenant_id,page_number,text) VALUES(%s,%s,1,%s)',(docs[0],tenant,long_text))
        passages=split_passages(long_text)
        for index,(start,end,passage) in enumerate(passages[:2]):
            key=hashlib.sha256(f'{docs[0]}:1:{start}:{passage}'.encode()).hexdigest()
            revision='mechanical-test-only' if index==0 else 'obsolete-model-revision'
            conn.execute("INSERT INTO private.passage_index VALUES(%s,%s,%s,1,%s,%s,%s,false,to_tsvector('simple',public.unaccent(%s)),%s,%s)",
                         (key,docs[0],tenant,start,end,passage,passage,Vector([1.0]+[0.0]*1023),revision))
    db=Database(settings.database_url);await db.open();context=TenantContext(user_id=user,tenant_id=tenant,role='admin');retriever=PrivateRetriever(db,FixedVectors())
    try:
        response=await retriever.ainvoke({'context':context,'ids':docs,'query':'tenant protections'})
        assert {r['document_id'] for r in response['results']}==set(docs)
        assert all(any(r['document_id']==doc and any(e['engine']=='private_semantic' for e in r['retrieval_evidence']) for r in response['results']) for doc in docs)
        assert 'PRIVATE_INDEX_PENDING' in response['warnings']
        complete=await retriever.ainvoke({'context':context,'ids':[docs[1]],'query':'tenant protections'})
        assert 'PRIVATE_INDEX_PENDING' not in complete['warnings']
        with psycopg.connect(settings.admin_database_url) as conn:
            conn.execute("INSERT INTO private.jobs(tenant_id,document_id,kind,status,deletion_epoch) VALUES(%s,%s,'index','retry',0)",(tenant,docs[1]))
        partial=await retriever.ainvoke({'context':context,'ids':[docs[1]],'query':'tenant protections'})
        assert 'PRIVATE_INDEX_PENDING' in partial['warnings']
        with pytest.raises(DomainError):await retriever.authorize(context,docs+[uuid4()])
        with psycopg.connect(settings.admin_database_url) as conn:conn.execute('UPDATE private.documents SET trashed_at=now() WHERE id=%s',(docs[0],))
        with pytest.raises(DomainError):await retriever.ainvoke({'context':context,'ids':docs,'query':'tenant protections'})
    finally:
        await db.close()
        with psycopg.connect(settings.admin_database_url) as conn:
            for table in ('jobs','passage_index','chunks','documents','tenant_members'):conn.execute(f'DELETE FROM private.{table} WHERE tenant_id=%s',(tenant,))
            conn.execute('DELETE FROM private.tenants WHERE id=%s',(tenant,))
