"""Import official DOGC originals. Bounded runs and missing history never pass coverage."""
import argparse,sys,json
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.dogc import DOGCAdapter
from services.ingest.ingest.pipeline import ingest_window


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--limit',type=int,default=10);p.add_argument('--all',action='store_true');p.add_argument('--skip-existing',action='store_true',help='Initial original-publication backfill only; does not refresh prior records');args=p.parse_args()
    if args.limit<=0:p.error('Use a positive limit or --all')
    settings=Settings();adapter=DOGCAdapter()
    with psycopg.connect(settings.ingest_database_url) as conn:
        if not conn.execute('SELECT pg_try_advisory_lock(149730)').fetchone()[0]:raise RuntimeError('DOGC source writer already active')
        if args.skip_existing:
            if not args.all:p.error('--skip-existing requires --all')
            adapter.known_ids={row[0] for row in conn.execute("SELECT external_id FROM legal.instruments WHERE source_id='DOGC_NORMATIVE'")}
        conn.execute("INSERT INTO legal.sources(id,name,official_url,terms_url,adapter,limitations) VALUES('DOGC_NORMATIVE','DOGC / Portal Jurídic · normative catalogue','https://dogc.gencat.cat/es/serveis/Dades_obertes/','https://administraciodigital.gencat.cat/ca/dades/dades-obertes/informacio-practica/llicencies/','dogc','[\"Archive reconciliation, binary annexes and reuse approval pending\"]') ON CONFLICT DO NOTHING");conn.commit()
        try:result=ingest_window(conn,adapter,settings.public_storage_path,limit=None if args.all else args.limit,jurisdiction_resolver=lambda parsed:'ES-AUTO-09')
        finally:adapter.close()
        result['skipped_existing_ids']=len(adapter.known_ids)
        result['skip_existing_limitation']='Initial original-publication backfill; prior records/history still need independent refresh/reconciliation.' if args.skip_existing else None
    (ROOT/'verification/reports/dogc-ingestion.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
