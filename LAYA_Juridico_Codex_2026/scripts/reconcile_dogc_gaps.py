"""Retry the captured DOGC preview gaps while preserving missing official language warnings."""
import json,sys
from pathlib import Path
from datetime import datetime,timezone
import psycopg,httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.dogc import DOGCAdapter,API
from services.ingest.ingest.contracts import PublicationRef
from services.ingest.ingest.pipeline import store_publication
from datetime import date


def main():
    previous=json.loads((ROOT/'verification/reports/dogc-ingestion.json').read_text());identities=[gap.split(':')[0].removeprefix('DOGC-') for gap in previous['gaps'] if ':INGEST_FAILED' in gap];settings=Settings();adapter=DOGCAdapter();rows=[]
    try:
        with psycopg.connect(settings.ingest_database_url) as conn:
            for identity in identities:
                observation={'external_id':'DOGC-'+identity}
                try:
                    url=str(httpx.URL(API,params={'n_mero_de_control':identity}));metadata=adapter.http.get(url).json()[0]
                    raw=adapter.fetch(PublicationRef(adapter.source_id,'DOGC-'+identity,url,date.fromisoformat(metadata['data_de_publicaci_del_diari'][:10])));parsed=adapter.parse(raw);store_publication(conn,parsed,raw,settings.public_storage_path,'ES-AUTO-09');conn.commit()
                    observation.update({'status':'integrated','versions':len(parsed.versions),'warnings':list(parsed.ingestion_warnings)})
                except Exception as error:conn.rollback();observation.update({'status':'blocked','failure_code':type(error).__name__})
                rows.append(observation);print(f'DOGC recovery {len(rows)}/{len(identities)}: {observation["status"]}',flush=True)
    finally:adapter.close()
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'partial','resolved':sum(r['status']=='integrated' for r in rows),'remaining':sum(r['status']=='blocked' for r in rows),'records':rows,'limitations':['Targeted recovery only. Missing official XML language variants, annexes, available history and full catalogue/coverage remain unverified.']}
    (ROOT/'verification/reports/dogc-reconciliation.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
