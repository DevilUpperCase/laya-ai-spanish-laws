"""Record actual versions, lock hashes, database counts and sanitized local readiness."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import sys
from datetime import datetime,timezone
from pathlib import Path
import httpx
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.api.app.main import create_app


def main():
    settings=Settings()
    packages={}
    for name in ("fastapi","langchain-core","langgraph","laya","psycopg","pgvector","torch","transformers","sentence-transformers","pymupdf","python-docx"):
        distribution=metadata.metadata(name)
        packages[name]={"version":metadata.version(name),"license_metadata":distribution.get("License-Expression") or distribution.get("License"),"license_review":"pending"}
    locks={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/"uv.lock",ROOT/"apps/web/package-lock.json")}
    now=datetime.now(timezone.utc).isoformat()
    dependencies={"status":"observed","generated_at":now,"python":platform.python_version(),"packages":packages,"lock_sha256":locks,"models":json.loads((ROOT/"verification/model-artifacts.json").read_text()),"license_approval":"pending"}
    (ROOT/"verification/dependency-pins.json").write_text(json.dumps(dependencies,indent=2)+"\n")
    (ROOT/"docs/contracts/openapi.json").write_text(json.dumps(create_app(settings,connect=False).openapi(),indent=2)+"\n")
    with psycopg.connect(settings.ingest_database_url) as conn:
        counts={table:conn.execute("SELECT count(*) FROM legal."+table).fetchone()[0] for table in ("jurisdictions","sources","instruments","publications","section_versions","chunks")}
        counts["embedded_chunks"]=conn.execute("SELECT count(*) FROM legal.chunks WHERE embedding IS NOT NULL AND embedding_revision=%s",(settings.embedding_model_revision,)).fetchone()[0]
        counts["current_observed_chunks"]=conn.execute("SELECT count(*) FROM legal.chunks WHERE version_id IN (SELECT version_id FROM legal.current_versions_cache)").fetchone()[0]
        counts['current_embedded_chunks']=conn.execute("SELECT count(*) FROM legal.chunks WHERE version_id IN (SELECT version_id FROM legal.current_versions_cache) AND embedding IS NOT NULL AND embedding_revision=%s",(settings.embedding_model_revision,)).fetchone()[0]
        counts['current_cache_as_of']=str(conn.execute('SELECT as_of FROM legal.current_cache_metadata WHERE singleton').fetchone()[0])
        runs=[dict(zip(("status","discovered","integrated"),row)) for row in conn.execute("SELECT status,discovered_count,integrated_count FROM legal.ingest_runs ORDER BY started_at DESC LIMIT 3").fetchall()]
    with httpx.Client(trust_env=False,timeout=120) as client:
        health=client.get("http://127.0.0.1:8000/health")
        ready=client.get("http://127.0.0.1:8000/ready",headers={"Authorization":"Bearer "+settings.internal_api_key})
    report={"generated_at":now,"scope":"local_development","counts":counts,"recent_imports":runs,"liveness":health.status_code,"readiness":ready.json(),
            "local_ocr":{"enabled":settings.ocr_enabled,"revision":settings.ocr_model_revision,"languages":settings.ocr_language},
            "limitations":["Vector indexing is partial until every required chunk has the pinned revision.","BOE catalogue and targeted recovery plus partial DOGC/DOG imports; publisher/national coverage audits remain incomplete.","Normal local password login and private restore rehearsal passed; professional evaluation, elapsed backup-expiry proof, independent replication and production deployment remain pending."]}
    (ROOT/"verification/reports/runtime.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
