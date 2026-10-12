import json
from pathlib import Path
import sys
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings


if __name__=="__main__":
    with psycopg.connect(Settings().ingest_database_url) as conn:
        print(json.dumps({table:conn.execute("SELECT count(*) FROM legal."+table).fetchone()[0] for table in ("jurisdictions","sources","instruments","section_versions","chunks","publications")},indent=2))
        print("Current observed chunks:",conn.execute("SELECT count(*) FROM legal.chunks WHERE version_id IN (SELECT DISTINCT ON(section_id) id FROM legal.section_versions ORDER BY section_id,consolidation_date DESC,source_order DESC,id DESC)").fetchone()[0])
        print("Embedded chunks:",conn.execute("SELECT count(*) FROM legal.chunks WHERE embedding IS NOT NULL").fetchone()[0])
        print("Runs:",conn.execute("SELECT status,discovered_count,integrated_count,failure_code FROM legal.ingest_runs ORDER BY started_at DESC LIMIT 3").fetchall())
