"""Import reviewed enumerated norms at any verified geographic identity; no coverage approval."""
import argparse,json,sys
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.manifest import load_manifest,ManifestAdapter
from services.ingest.ingest.pipeline import store_publication
from psycopg.types.json import Jsonb


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);args=p.parse_args()
    data=load_manifest(args.manifest,ROOT/'sources');settings=Settings();adapter=ManifestAdapter(data,settings)
    report={'source_id':data['source_id'],'status':'partial','integrated':0,'gaps':list(adapter.inherent_gaps)}
    try:
        with psycopg.connect(settings.ingest_database_url) as conn:
            existing=conn.execute('SELECT official_url FROM legal.sources WHERE id=%s',(adapter.source_id,)).fetchone()
            if existing and existing[0]!=data['official_url']:raise ValueError('Source ID already belongs to a different official publisher')
            conn.execute("INSERT INTO legal.sources(id,name,official_url,terms_url,adapter,limitations) VALUES(%s,%s,%s,%s,'manifest',%s) ON CONFLICT DO NOTHING",(adapter.source_id,data['name'],data['official_url'],data['terms_url'],Jsonb(list(adapter.inherent_gaps))));conn.commit()
            for ref in adapter.discover(None,None,None).publications:
                row=adapter.rows[ref.external_id]
                if not conn.execute('SELECT 1 FROM legal.jurisdictions WHERE id=%s',(row['jurisdiction_id'],)).fetchone():raise ValueError('Manifest jurisdiction does not exist in official inventory')
                try:
                    raw=adapter.fetch(ref);parsed=adapter.parse(raw);store_publication(conn,parsed,raw,settings.public_storage_path,row['jurisdiction_id']);conn.commit();report['integrated']+=1
                except Exception:conn.rollback();report['gaps'].append(row['external_id']+':INGEST_FAILED')
    finally:adapter.close()
    (ROOT/'verification/reports'/('manifest-'+data['source_id']+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
