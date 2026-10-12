"""Capture Galicia's current general-disposition RSS preview; archive/freshness remains blocked."""
import json,sys
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.dog import DOGAdapter
from services.ingest.ingest.pipeline import ingest_window


if __name__=='__main__':
    settings=Settings();adapter=DOGAdapter()
    with psycopg.connect(settings.ingest_database_url) as conn:
        conn.execute("INSERT INTO legal.sources(id,name,official_url,terms_url,adapter,limitations) VALUES('DOG_GENERAL','DOG · disposiciones generales RSS','https://www.xunta.gal/diario-oficial-galicia/suscricionsRSS.do?lang=es','https://www.xunta.gal/aviso-legal','dog','[\"RSS preview; history, normative rules and freshness approval pending\"]') ON CONFLICT DO NOTHING");conn.commit()
        try:report=ingest_window(conn,adapter,settings.public_storage_path,jurisdiction_resolver=lambda parsed:'ES-AUTO-12')
        finally:adapter.close()
    (ROOT/'verification/reports/dog-ingestion.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
