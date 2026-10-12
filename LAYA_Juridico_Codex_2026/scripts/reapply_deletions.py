"""Offline restore barrier. Keep API stopped, preserve newest independent journal."""
import argparse
import sys
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.api.app.deletion_journal import read_journal


def reapply(conn,records):
    for record in records:
        row=conn.execute("SELECT id FROM private.documents WHERE id=%s AND tenant_id=%s FOR UPDATE",(record["document_id"],record["tenant_id"])).fetchone()
        if not row:continue
        conn.execute("UPDATE private.documents SET deleted_at=coalesce(deleted_at,%s),deletion_epoch=greatest(deletion_epoch,%s),parse_status='deleted',purge_due_at=now(),purged_at=NULL WHERE id=%s",(record["deleted_at"],record["epoch"],record["document_id"]))
        conn.execute("UPDATE private.jobs SET status='cancelled',lease_token=NULL WHERE document_id=%s AND kind IN ('extract','index')",(record["document_id"],))
        conn.execute("INSERT INTO private.deletion_records VALUES(%s,%s,%s,now(),NULL,%s::timestamptz+interval '30 days',%s) ON CONFLICT(document_id) DO UPDATE SET purged_at=NULL,purge_due_at=now()",(record["document_id"],record["tenant_id"],record["deleted_at"],record["deleted_at"],record["epoch"]))
        conn.execute("INSERT INTO private.jobs(document_id,tenant_id,kind,deletion_epoch) SELECT %s,%s,'purge',%s WHERE NOT EXISTS(SELECT 1 FROM private.jobs WHERE document_id=%s AND kind='purge' AND status IN ('queued','retry','processing')) ON CONFLICT(document_id,kind,deletion_epoch) DO UPDATE SET status='queued',next_attempt=now(),lease_until=NULL,lease_token=NULL,failure_code=NULL WHERE private.jobs.status NOT IN ('queued','retry','processing')",(record["document_id"],record["tenant_id"],record["epoch"],record["document_id"]))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maintenance-confirmed",action="store_true",required=True,help="Operator confirms API closed and independent journal current")
    args=parser.parse_args()
    settings=Settings()
    records=read_journal(settings.deletion_journal_path)
    with psycopg.connect(settings.admin_database_url) as conn:reapply(conn,records)
    print("Restore tombstones reapplied:",len(records),". Run purge worker and verify before reopening API.")
