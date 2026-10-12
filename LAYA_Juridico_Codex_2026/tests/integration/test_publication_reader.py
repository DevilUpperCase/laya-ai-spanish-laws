import httpx,pytest,psycopg
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import jwt
from services.api.app.config import Settings
from services.api.app.main import create_app

@pytest.mark.database
async def test_real_exact_version_and_original_reader():
    settings=Settings();tenant,user=uuid4(),uuid4()
    with psycopg.connect(settings.admin_database_url) as conn:
        conn.execute("INSERT INTO private.tenants VALUES(%s,'Reader mechanics')",(tenant,))
        conn.execute("INSERT INTO private.tenant_members VALUES(%s,%s,'reader')",(tenant,user))
        row=conn.execute("SELECT v.id,v.text FROM legal.section_versions v JOIN legal.sections s ON s.id=v.section_id WHERE s.instrument_id='BOE-A-1978-31229' LIMIT 1").fetchone()
    token=jwt.encode({'sub':str(user),'iss':settings.auth_issuer,'aud':settings.auth_audience,'iat':datetime.now(timezone.utc),'exp':datetime.now(timezone.utc)+timedelta(minutes=10)},settings.auth_private_key_path.read_bytes(),algorithm='RS256')
    headers={'Authorization':'Bearer '+token,'X-Tenant-ID':str(tenant)};app=create_app(settings)
    try:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response=await client.get('/v1/section-versions/'+row[0],headers=headers)
                assert response.status_code==200 and response.json()['text']==row[1]
                if response.json()['assets']:
                    original=await client.get('/v1/publication-assets/'+response.json()['assets'][0]['id']+'/download',headers=headers)
                    assert original.status_code==200 and original.content.startswith(b'%PDF-')
                assert (await client.get('/v1/section-versions/missing',headers=headers)).status_code==404
    finally:
        with psycopg.connect(settings.admin_database_url) as conn:
            conn.execute('DELETE FROM private.tenant_members WHERE tenant_id=%s',(tenant,));conn.execute('DELETE FROM private.tenants WHERE id=%s',(tenant,))
