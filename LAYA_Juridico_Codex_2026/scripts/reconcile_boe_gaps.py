"""Retry the exact failed BOE catalogue records without claiming a new full audit."""
import json,sys
from datetime import datetime,timezone
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.boe import BOEAdapter,BASE
from services.ingest.ingest.contracts import PublicationRef
from services.ingest.ingest.inventory import load_ine_snapshot
from services.ingest.ingest.jurisdiction_resolver import region_resolver
from services.ingest.ingest.pipeline import store_publication


def main():
    previous=json.loads((ROOT/'verification/reports/database-population.json').read_text())
    settings=Settings();adapter=BOEAdapter();resolve=region_resolver(load_ine_snapshot(ROOT/'sources/snapshots')[0])
    outcomes=[]
    with psycopg.connect(settings.ingest_database_url) as conn:
        run=conn.execute("INSERT INTO legal.ingest_runs(source_id) VALUES('BOE_CONSOLIDATED') RETURNING id").fetchone()[0];conn.commit()
        for gap in previous['live_import']['gaps']:
            identifier=gap.split(':')[0]
            try:
                raw=adapter.fetch(PublicationRef(adapter.source_id,identifier,BASE+'/id/'+identifier,None))
                parsed=adapter.parse(raw);jurisdiction=resolve(parsed)
                if not jurisdiction:raise ValueError('JURISDICTION_UNRESOLVED')
                store_publication(conn,parsed,raw,settings.public_storage_path,jurisdiction);conn.commit()
                outcomes.append({'id':identifier,'status':'integrated'})
            except Exception as e:
                conn.rollback();outcomes.append({'id':identifier,'status':'failed','failure':type(e).__name__})
            gaps=[r['id']+':RETRY_FAILED' for r in outcomes if r['status']=='failed']
            count=sum(r['status']=='integrated' for r in outcomes)
            conn.execute('UPDATE legal.ingest_runs SET discovered_count=%s,integrated_count=%s,gaps=%s WHERE id=%s',(len(outcomes),count,Jsonb(gaps),run));conn.commit()
            print(identifier,outcomes[-1]['status'],flush=True)
        conn.execute("UPDATE legal.ingest_runs SET status='partial',finished_at=now() WHERE id=%s",(run,));conn.commit()
        counts={t:conn.execute('SELECT count(*) FROM legal.'+t).fetchone()[0] for t in ('instruments','section_versions','chunks')}
    adapter.close()
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'targeted_gap_recovery','status':'resolved' if not gaps else 'partial','resolved':count,'remaining':gaps,'outcomes':outcomes,'counts':counts,'limitations':['Targeted retries do not certify a fresh whole-catalogue reconciliation or nationwide coverage.']}
    (ROOT/'verification/reports/boe-reconciliation.json').write_text(json.dumps(report,indent=2)+'\n')
    if gaps:raise SystemExit(1)


if __name__=='__main__':main()
