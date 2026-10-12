"""Prepare development-only secrets; start Docker DB; initialize restricted roles/auth keys."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import psycopg
from psycopg import sql
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    local = ROOT / "private-data"
    local.mkdir(exist_ok=True)
    path = local / "docker-secrets.json"
    if path.exists():
        credentials = json.loads(path.read_text())
    else:
        credentials = {key: secrets.token_urlsafe(36) for key in ("admin", "api", "ingest", "worker", "internal", "laya")}
        path.write_text(json.dumps(credentials))
    compose_env = local / "docker.env"
    compose_env.write_text("POSTGRES_PASSWORD=" + credentials["admin"] + "\n")
    subprocess.run(["docker", "compose", "--env-file", str(compose_env), "-f", str(ROOT / "infra/compose.yaml"), "up", "-d", "--wait", "--force-recreate", "db"], check=True)
    base = "postgresql://postgres:" + credentials["admin"] + "@127.0.0.1:15432/laya_juridico"
    with psycopg.connect(base, autocommit=True) as conn:
        for name in ("api", "ingest", "worker"):
            role = "laya_" + name
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(credentials[name])))
    auth = local / "auth"
    auth.mkdir(exist_ok=True)
    if not (auth / "private.pem").exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        (auth / "private.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        (auth / "public.pem").write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    env_path = ROOT / ".env"
    existing = env_path.read_text() if env_path.exists() else ""
    # Only replace an .env created for our own local bootstrap; never overwrite external configuration.
    if existing and not any(port in existing for port in ("@127.0.0.1:55432/laya_juridico", "@127.0.0.1:55433/laya_juridico", "@127.0.0.1:15432/laya_juridico")):
        raise ValueError("An external .env exists; keep it and configure Docker credentials separately")
    lines = ["APP_ENV=development", "AUTH_ISSUER=http://127.0.0.1:8000/local-auth", "AUTH_AUDIENCE=laya-juridico", "ADMIN_DATABASE_URL=" + base]
    for name, variable in (("api", "DATABASE_URL"), ("ingest", "INGEST_DATABASE_URL"), ("worker", "WORKER_DATABASE_URL")):
        lines.append(variable + "=postgresql://laya_" + name + ":" + credentials[name] + "@127.0.0.1:15432/laya_juridico")
    lines += ["INTERNAL_API_KEY=" + credentials["internal"], "LAYA_API_KEY=" + credentials["laya"], "LAYA_BASE_URL=http://127.0.0.1:8001", "LANGCHAIN_TRACING_V2=false", "LANGSMITH_TRACING=false"]
    retained = [line for line in existing.splitlines() if line.startswith(("EMBEDDING_", "LAYA_MODEL_REVISION=", "OCR_",'SUPABASE_AUTH_','BROWSER_SESSION_','CLAMAV_','CORS_ORIGINS=','BACKUP_'))]
    env_path.write_text("\n".join(lines + retained) + "\n", encoding="utf-8")
    from scripts.migrate import migrate
    migrate(base)
    print("Docker development database initialized on loopback port 15432; secrets remain in .env.")


if __name__ == "__main__":
    main()
