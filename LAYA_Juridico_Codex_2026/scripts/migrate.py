"""Transactional, checksum-tracked migrations. Admin connection used only by this CLI."""
from pathlib import Path
import argparse
import hashlib
import sys
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.api.app.config import Settings


def migrate(url: str):
    if not url:
        raise ValueError("ADMIN_DATABASE_URL is required")
    with psycopg.connect(url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(149726)")
        for role in ("laya_api", "laya_ingest", "laya_worker"):
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS").format(sql.Identifier(role)))
        conn.execute("CREATE TABLE IF NOT EXISTS public.schema_migrations(name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
        for path in sorted((ROOT / "db/migrations").glob("*.sql")):
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            existing = conn.execute("SELECT sha256 FROM public.schema_migrations WHERE name=%s", (path.name,)).fetchone()
            if existing:
                if existing[0] != digest:
                    raise ValueError("Applied migration checksum changed: " + path.name)
                continue
            conn.execute(content.decode("utf-8"))
            conn.execute("INSERT INTO public.schema_migrations(name,sha256) VALUES(%s,%s)", (path.name, digest))
            print("Applied", path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    migrate(Settings().admin_database_url)
