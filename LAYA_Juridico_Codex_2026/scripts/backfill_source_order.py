from pathlib import Path
import sys
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.boe import BOEAdapter


if __name__=="__main__":
    settings=Settings()
    count=0
    with psycopg.connect(settings.ingest_database_url) as conn:
        rows=conn.execute("SELECT object_key,official_url FROM legal.publications ORDER BY fetched_at").fetchall()
        for key,url in rows:
            parsed=BOEAdapter.parse_xml((settings.public_storage_path/key).read_bytes(),url)
            for version in parsed.versions:
                conn.execute("UPDATE legal.section_versions SET source_order=%s WHERE id=%s",(version.source_order,version.id))
                count+=1
        conn.commit()
    print("Backfilled official XML ordering for",count,"observed section versions")
