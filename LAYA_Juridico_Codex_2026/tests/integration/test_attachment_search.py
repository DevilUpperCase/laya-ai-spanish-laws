from types import SimpleNamespace
from uuid import uuid4
import pytest,psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.contracts import TenantContext
from services.api.app.private_retrieval import PrivateRetriever
from services.api.app.errors import DomainError

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
    db=Database(settings.database_url);await db.open();context=TenantContext(user_id=user,tenant_id=tenant,role='admin');retriever=PrivateRetriever(db,FixedVectors())
    try:
        response=await retriever.ainvoke({'context':context,'ids':docs,'query':'tenant protections'})
        assert {r['document_id'] for r in response['results']}==set(docs)
        assert all(any(e['engine']=='private_semantic' for e in r['retrieval_evidence']) for r in response['results'])
        with psycopg.connect(settings.admin_database_url) as conn:
            conn.execute("INSERT INTO private.jobs(tenant_id,document_id,kind,status,deletion_epoch) VALUES(%s,%s,'index','retry',0)",(tenant,docs[0]))
        partial=await retriever.ainvoke({'context':context,'ids':docs,'query':'tenant protections'})
        assert 'PRIVATE_INDEX_PENDING' in partial['warnings']
        with pytest.raises(DomainError):await retriever.authorize(context,docs+[uuid4()])
        with psycopg.connect(settings.admin_database_url) as conn:conn.execute('UPDATE private.documents SET trashed_at=now() WHERE id=%s',(docs[0],))
        with pytest.raises(DomainError):await retriever.ainvoke({'context':context,'ids':docs,'query':'tenant protections'})
    finally:
        await db.close()
        with psycopg.connect(settings.admin_database_url) as conn:
            for table in ('jobs','passage_index','documents','tenant_members'):conn.execute(f'DELETE FROM private.{table} WHERE tenant_id=%s',(tenant,))
            conn.execute('DELETE FROM private.tenants WHERE id=%s',(tenant,))
