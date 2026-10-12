"""Load official geography/directory and real BOE XML. Bounded imports are partial."""
import argparse
import json
from pathlib import Path
import sys
import psycopg
from psycopg.types.json import Jsonb

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.boe import BOEAdapter
from services.ingest.ingest.contracts import PublicationRef,RawPublication
from services.ingest.ingest.inventory import load_ine_snapshot,write_inventory
from services.ingest.ingest.source_registry import directory_sources
from services.ingest.ingest.pipeline import store_publication,ingest_window
from services.ingest.ingest.jurisdiction_resolver import region_resolver


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boe-limit",type=int,default=0,help="Additional live BOE records; bounded catalogue imports remain partial")
    parser.add_argument("--boe-all",action="store_true",help="Entire consolidated catalogue; does not prove nationwide scope")
    args=parser.parse_args()
    if args.boe_limit<0:parser.error("Limit must be nonnegative")
    settings=Settings()
    entities,limitations=load_ine_snapshot(ROOT/"sources/snapshots")
    sources=directory_sources((ROOT/"sources/snapshots/boe-directory.html").read_bytes())
    with psycopg.connect(settings.ingest_database_url) as conn:
        pending=entities.copy()
        written=set()
        while pending:
            ready=[e for e in pending if e["parent_id"] is None or e["parent_id"] in written]
            if not ready:raise ValueError("Inventory hierarchy cycle")
            for e in ready:
                conn.execute("""INSERT INTO legal.jurisdictions(id,level,parent_id,name,official_source_url,inventory_revision,verified)
                VALUES(%s,%s,%s,%s,%s,%s,false) ON CONFLICT(id) DO UPDATE SET name=excluded.name,inventory_revision=excluded.inventory_revision,official_source_url=excluded.official_source_url""",
                tuple(e[k] for k in ("id","level","parent_id","name","official_source_url","inventory_revision")))
                written.add(e["id"])
                pending.remove(e)
        for source in sources:
            conn.execute("INSERT INTO legal.sources(id,name,official_url,terms_url,adapter,audit_status,limitations) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",
                tuple(source[k] for k in ("id","name","official_url","terms_url","adapter","audit_status"))+(Jsonb(limitations if source["id"]=="BOE_CONSOLIDATED" else ["Directory entry only; no audited ingestion"]),))
        conn.execute("UPDATE legal.sources SET limitations=%s WHERE id='BOE_CONSOLIDATED'",(Jsonb(limitations),))
        conn.commit()
        fixture_count=0
        for path in sorted((ROOT/"tests/fixtures/boe").glob("BOE-A-*.xml")):
            meta=json.loads(path.with_suffix(".xml.metadata.json").read_text())
            parsed=BOEAdapter.parse_xml(path.read_bytes(),meta["url"])
            raw=RawPublication(PublicationRef("BOE_CONSOLIDATED",parsed.external_id,meta["url"],parsed.publication_date),path.read_bytes())
            store_publication(conn,parsed,raw,settings.public_storage_path,"ES")
            fixture_count+=1
        conn.commit()
        live=None
        if args.boe_limit or args.boe_all:
            adapter=BOEAdapter()
            try:live=ingest_window(conn,adapter,settings.public_storage_path,limit=None if args.boe_all else args.boe_limit,jurisdiction_resolver=region_resolver(entities))
            finally:adapter.close()
        counts={name:conn.execute("SELECT count(*) FROM legal."+name).fetchone()[0] for name in ("jurisdictions","sources","instruments","section_versions","chunks","publications")}
    output=ROOT/"verification/evidence/jurisdictions.csv"
    write_inventory(entities,output)
    report={"status":"internal_partial","counts":counts,"official_fixture_instruments":fixture_count,"live_import":live,
         "limitations":limitations+["Publisher adapters and nationwide/current/history audits incomplete.","Inventory awaits independent review; legal effectiveness unverified."]}
    path=ROOT/"verification/reports/database-population.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=="__main__":main()
