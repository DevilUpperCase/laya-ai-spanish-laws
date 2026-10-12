"""Revoke only this local session's explicitly synthetic browser-check uploads."""
import json
import sys
from pathlib import Path
import httpx
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings


if __name__=="__main__":
    session=json.loads((ROOT/"private-data/local-session.json").read_text())
    with psycopg.connect(Settings().admin_database_url) as conn:
        ids=conn.execute("SELECT id FROM private.documents WHERE tenant_id=%s AND filename='browser-synthetic.pdf' AND deleted_at IS NULL",(session["tenant_id"],)).fetchall()
    with httpx.Client(trust_env=False,timeout=30) as client:
        for (identifier,) in ids:
            response=client.delete("http://127.0.0.1:8000/v1/documents/"+str(identifier),headers={"Authorization":"Bearer "+session["token"],"X-Tenant-ID":session["tenant_id"]})
            response.raise_for_status()
    print("Synthetic browser uploads revoked:",len(ids))
