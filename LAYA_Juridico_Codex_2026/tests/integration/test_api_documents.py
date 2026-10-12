from io import BytesIO
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import asyncio
import httpx
import jwt
import psycopg
import pytest
import pymupdf
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.database import Database
from services.api.app.jobs import JobWorker


@pytest.mark.database
@pytest.mark.parametrize("scanned",[False,True])
async def test_real_upload_processing_selection_and_delete(tmp_path,scanned):
    settings=Settings(private_storage_path=tmp_path/"objects")
    user,a,b=uuid4(),uuid4(),uuid4()
    with psycopg.connect(settings.admin_database_url) as conn:
        conn.execute("INSERT INTO private.tenants VALUES(%s,'Synthetic API A'),(%s,'Synthetic API B')",(a,b))
        conn.execute("INSERT INTO private.tenant_members VALUES(%s,%s,'admin'),(%s,%s,'admin')",(a,user,b,user))
    now=datetime.now(timezone.utc)
    token=jwt.encode({"sub":str(user),"iss":settings.auth_issuer,"aud":settings.auth_audience,"iat":now,"exp":now+timedelta(minutes=5)},settings.auth_private_key_path.read_bytes(),algorithm="RS256")
    headers={"Authorization":"Bearer "+token,"X-Tenant-ID":str(a)}
    app=create_app(settings)
    worker_db=Database(settings.worker_database_url,worker=True)
    await worker_db.open()
    worker=JobWorker(worker_db,settings)
    try:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
                pdf=pymupdf.open();pdf.new_page().insert_text((50,50),"Canary private document: vivienda arrendamiento");data=pdf.tobytes()
                if scanned:
                    image=pdf[0].get_pixmap(dpi=200,alpha=False)
                    scan=pymupdf.open();scan.new_page().insert_image(scan[0].rect,stream=image.tobytes("png"));data=scan.tobytes()
                response=await client.post("/v1/documents",headers={**headers,"Idempotency-Key":"one"},files={"file":("synthetic.pdf",data,"application/pdf")})
                assert response.status_code==202
                doc_id=response.json()["id"]
                assert (await client.get("/v1/documents/"+doc_id,headers={**headers,"X-Tenant-ID":str(b)})).status_code==404
                assert await worker.run_once(doc_id)
                response=await client.get("/v1/documents/"+doc_id,headers=headers)
                assert response.json()["parse_status"]=="ready"
                text=response.json()["pages"][0]["text"]
                assert "Canary private" in text
                assert response.json()["pages"][0]["ocr_uncertain"] is scanned
                download=await client.get("/v1/documents/"+doc_id+"/download",headers=headers)
                assert download.content==data
                deleted=await client.delete("/v1/documents/"+doc_id,headers=headers)
                assert deleted.status_code==204
                assert (await client.delete("/v1/documents/"+doc_id,headers=headers)).status_code==204
                assert (await client.get("/v1/documents/"+doc_id,headers=headers)).status_code==404
                assert (await client.get("/v1/documents/"+doc_id+"/download",headers=headers)).status_code==404
                selection={"page_number":1,"start_offset":0,"end_offset":6,"selected_text":"Canary"}
                assert (await client.post("/v1/documents/"+doc_id+"/search-related",headers=headers,json=selection)).status_code==404
                assert await worker.run_once(doc_id)
                with psycopg.connect(settings.admin_database_url) as conn:
                    assert conn.execute("SELECT count(*) FROM private.chunks WHERE document_id=%s",(doc_id,)).fetchone()[0]==0
                    assert conn.execute("SELECT purged_at IS NOT NULL FROM private.documents WHERE id=%s",(doc_id,)).fetchone()[0]
                assert not any(p.is_file() for p in settings.private_storage_path.rglob("*"))
    finally:
        await worker_db.close()
        with psycopg.connect(settings.admin_database_url) as conn:
            for table in ("jobs","passage_index","chunks","deletion_records","documents","tenant_members","tenants"):
                key="id" if table=="tenants" else "tenant_id"
                conn.execute(f"DELETE FROM private.{table} WHERE {key}=ANY(%s)",([a,b],))


@pytest.mark.database
async def test_invalid_auth_and_private_validation_are_sanitized():
    settings=Settings()
    app=create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            assert (await client.post("/v1/search",headers={"Authorization":"Bearer forged","X-Tenant-ID":str(uuid4())},json={"query":"private canary"})).status_code==401
            response=await client.post("/v1/search",json={"query":"PRIVATE_CANARY_DO_NOT_LOG","unknown":"private"})
            assert "PRIVATE_CANARY_DO_NOT_LOG" not in response.text


def test_settings_repr_never_contains_secrets():
    settings=Settings(database_url="postgresql://CANARY_SECRET",laya_api_key="CANARY_SECRET",internal_api_key="CANARY_SECRET")
    assert "CANARY_SECRET" not in repr(settings)
