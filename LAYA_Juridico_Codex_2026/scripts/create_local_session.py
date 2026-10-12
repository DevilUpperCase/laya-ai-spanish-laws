"""Create a development tenant/session. Writes credentials to ignored local file only."""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys
from uuid import uuid4
import jwt
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name",default="Local development")
    args=parser.parse_args()
    settings=Settings()
    if settings.app_env!="development":raise ValueError("Use self-hosted production authentication in production")
    path=ROOT/"private-data/local-session.json"
    previous=json.loads(path.read_text()) if path.exists() else {}
    tenant=previous.get("tenant_id") or str(uuid4())
    user=previous.get("user_id") or str(uuid4())
    with psycopg.connect(settings.admin_database_url) as conn:
        conn.execute("INSERT INTO private.tenants VALUES(%s,%s) ON CONFLICT DO NOTHING",(tenant,args.name))
        conn.execute("INSERT INTO private.tenant_members VALUES(%s,%s,'admin') ON CONFLICT DO NOTHING",(tenant,user))
    now=datetime.now(timezone.utc)
    token=jwt.encode({"sub":user,"iss":settings.auth_issuer,"aud":settings.auth_audience,"iat":now,"exp":now+timedelta(hours=8)},settings.auth_private_key_path.read_bytes(),algorithm="RS256")
    path.write_text(json.dumps({"tenant_id":tenant,"user_id":user,"token":token,"expires_at":(now+timedelta(hours=8)).isoformat()},indent=2))
    print("Development session saved to private-data/local-session.json; valid for 8 hours.")
