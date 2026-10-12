"""Reconcile a BOE update-date window; unsupported publishers remain explicit gaps."""
import argparse
from datetime import date,timedelta
import json
from pathlib import Path
import sys
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.boe import BOEAdapter
from services.ingest.ingest.inventory import load_ine_snapshot
from services.ingest.ingest.jurisdiction_resolver import region_resolver
from services.ingest.ingest.pipeline import ingest_window


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date",type=date.fromisoformat,default=date.today()-timedelta(days=7))
    parser.add_argument("--to-date",type=date.fromisoformat,default=date.today())
    args=parser.parse_args()
    if args.from_date>args.to_date:parser.error("Invalid date window")
    settings=Settings()
    entities,_=load_ine_snapshot(ROOT/"sources/snapshots")
    adapter=BOEAdapter()
    try:
        with psycopg.connect(settings.ingest_database_url) as conn:
            conn.execute('SELECT legal.refresh_current_versions()');conn.commit()
            result=ingest_window(conn,adapter,settings.public_storage_path,start_date=args.from_date,end_date=args.to_date,jurisdiction_resolver=region_resolver(entities))
    finally:adapter.close()
    print(json.dumps(result))
    if result["status"]!="complete":raise SystemExit(1)
