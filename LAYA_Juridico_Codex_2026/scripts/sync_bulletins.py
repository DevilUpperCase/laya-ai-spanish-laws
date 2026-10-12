"""Reconcile BOE/BORME daily items, including individual notices. No national-complete claim."""
import argparse,json,sys
from pathlib import Path
from datetime import date,timedelta,datetime,timezone
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.official_http import OfficialHTTP
from services.ingest.ingest.bulletin_pipeline import sync_day

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',choices=['boe','borme','both'],default='both')
    parser.add_argument('--from-date',type=date.fromisoformat,default=date.today()-timedelta(days=7));parser.add_argument('--to-date',type=date.fromisoformat,default=date.today())
    parser.add_argument('--max-items',type=int);args=parser.parse_args()
    if args.from_date>args.to_date or (args.max_items is not None and args.max_items<1):parser.error('Invalid window or item limit')
    settings=Settings();client=OfficialHTTP({'www.boe.es'},max_bytes=128*1024*1024);client.client.headers['Accept']='application/xml';results=[]
    try:
        with psycopg.connect(settings.ingest_database_url) as conn:
            if not conn.execute('SELECT pg_try_advisory_lock(149731)').fetchone()[0]:raise RuntimeError('Bulletin synchronization already running')
            day=args.from_date
            while day<=args.to_date:
                for source in (['boe','borme'] if args.source=='both' else [args.source]):results.append(sync_day(conn,client,source,day,settings,args.max_items))
                day+=timedelta(days=1)
    finally:client.close()
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'windows':results,'national_complete':False,'limitations':['BOE/BORME adapters only; other required publishers/history/terms remain unverified.','Attached annex and subitem completeness requires source review. 404 alone is not proof of a legitimate no-issue day.']}
    (ROOT/'verification/reports/bulletin-sync.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    return int(any(r['status']!='complete' for r in results))
if __name__=='__main__':raise SystemExit(main())
