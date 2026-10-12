"""Development Supabase Auth bootstrap; preserves existing data and account identity."""
from pathlib import Path
import json, secrets, subprocess, sys
from datetime import datetime, timezone, timedelta
import httpx, jwt, psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings


def main():
    settings=Settings()
    if settings.app_env!='development':raise RuntimeError('Development bootstrap only')
    private=ROOT/'private-data'
    path=private/'auth-secrets.json'
    secret=json.loads(path.read_text()) if path.exists() else {'password':secrets.token_urlsafe(36),'jwt':secrets.token_urlsafe(48)}
    path.write_text(json.dumps(secret),encoding='utf-8')
    with psycopg.connect(settings.admin_database_url,autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='laya_auth'").fetchone():
            conn.execute(sql.SQL('CREATE ROLE laya_auth LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD {}').format(sql.Literal(secret['password'])))
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname='laya_auth'").fetchone():
            conn.execute('CREATE DATABASE laya_auth OWNER laya_auth')
        conn.execute('REVOKE CONNECT ON DATABASE laya_auth FROM PUBLIC')
        conn.execute('GRANT CONNECT ON DATABASE laya_auth TO laya_auth')
        conn.execute('ALTER ROLE laya_auth SET search_path TO auth')
    auth_url='postgresql://laya_auth:'+secret['password']+'@127.0.0.1:15432/laya_auth'
    with psycopg.connect(auth_url) as conn:
        conn.execute('CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION laya_auth')
        conn.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
    docker_secrets=json.loads((private/'docker-secrets.json').read_text())
    auth_env=private/'auth.env'
    auth_env.write_text('POSTGRES_PASSWORD='+docker_secrets['admin']+'\nAUTH_DATABASE_URL='+auth_url.replace('127.0.0.1:15432','db:5432')+'\nAUTH_JWT_SECRET='+secret['jwt']+'\n')
    subprocess.run(['docker','compose','--env-file',str(auth_env),'-f',str(ROOT/'infra/compose.yaml'),'-f',str(ROOT/'infra/auth.compose.yaml'),'up','-d','--wait','--no-recreate','auth'],check=True)
    local=json.loads((private/'local-session.json').read_text())
    credentials_path=private/'login-credentials.json'
    credentials=json.loads(credentials_path.read_text()) if credentials_path.exists() else {'email':'david@laya.local','password':secrets.token_urlsafe(20)}
    now=datetime.now(timezone.utc)
    admin=jwt.encode({'role':'service_role','aud':'authenticated','iat':now,'exp':now+timedelta(minutes=5)},secret['jwt'],algorithm='HS256')
    with httpx.Client(base_url='http://127.0.0.1:9999',trust_env=False,timeout=20,headers={'Authorization':'Bearer '+admin}) as client:
        existing=client.get('/admin/users/'+local['user_id'])
        if existing.status_code==404:
            response=client.post('/admin/users',json={**credentials,'id':local['user_id'],'email_confirm':True})
            if response.status_code not in {200,201}:raise RuntimeError('Local account creation failed: '+str(response.status_code))
            if response.json().get('id')!=local['user_id']:raise RuntimeError('Account identity mismatch')
        elif existing.status_code!=200:raise RuntimeError('Local account lookup failed: '+str(existing.status_code))
    credentials_path.write_text(json.dumps(credentials,indent=2),encoding='utf-8')
    env_path=ROOT/'.env'
    lines=[x for x in env_path.read_text().splitlines() if not x.startswith('SUPABASE_AUTH_URL=')]
    env_path.write_text('\n'.join(lines+['SUPABASE_AUTH_URL=http://127.0.0.1:9999'])+'\n',encoding='utf-8')
    print('Supabase Auth initialized. Login details are in private-data/login-credentials.json; no credentials printed.')


if __name__=='__main__':main()
