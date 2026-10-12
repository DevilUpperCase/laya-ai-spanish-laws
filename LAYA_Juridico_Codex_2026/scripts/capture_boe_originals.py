"""Capture explicitly selected original BOE PDFs; no unbounded download by default."""
import argparse,json,sys
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.boe_originals import capture_boe_original
from services.ingest.ingest.official_http import OfficialHTTP

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('ids',nargs='+');args=parser.parse_args()
    if len(args.ids)>100:parser.error('Maximum 100 explicitly selected records')
    settings=Settings();client=OfficialHTTP({'www.boe.es'},max_bytes=128*1024*1024);results=[]
    try:
        for identifier in args.ids:
            try:
                with psycopg.connect(settings.ingest_database_url) as conn:key=capture_boe_original(identifier,settings.public_storage_path,client,conn)
                results.append({'id':identifier,'asset_id':key,'status':'captured'})
            except Exception as error:results.append({'id':identifier,'status':'failed','error_type':type(error).__name__})
    finally:client.close()
    path=ROOT/'verification/reports/original-capture.json';path.write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
    return int(any(r['status']=='failed' for r in results))
if __name__=='__main__':raise SystemExit(main())
