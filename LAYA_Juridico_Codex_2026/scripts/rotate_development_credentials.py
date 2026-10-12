"""Rotate only credentials created by our Docker development bootstrap; never print them."""
from pathlib import Path
import json
import secrets
import sys
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings


if __name__=="__main__":
    settings=Settings()
    if "@127.0.0.1:15432/laya_juridico" not in settings.admin_database_url:
        raise ValueError("Only bootstrap-created local database credentials may be rotated")
    file=ROOT/"private-data/docker-secrets.json"
    previous=json.loads(file.read_text())
    new={key:secrets.token_urlsafe(36) for key in previous}
    with psycopg.connect(settings.admin_database_url,autocommit=True) as conn:
        for name in ("admin","api","ingest","worker"):
            role="postgres" if name=="admin" else "laya_"+name
            conn.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role),sql.Literal(new[name])))
    content=(ROOT/".env").read_text()
    for name,value in previous.items():content=content.replace(value,new[name])
    (ROOT/".env").write_text(content)
    file.write_text(json.dumps(new))
    (ROOT/"private-data/docker.env").write_text("POSTGRES_PASSWORD="+new["admin"]+"\n")
    print("Development database and service credentials rotated.")
