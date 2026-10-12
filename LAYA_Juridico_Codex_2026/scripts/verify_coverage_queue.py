"""Check per-jurisdiction reviewed audit rows against the actual official inventory."""
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.verify_package import artifact_path,read_json,check_source_audit,reviewed


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',type=Path,default=ROOT/'sources/nationwide-review-queue.csv');args=p.parse_args()
    with (ROOT/'verification/evidence/jurisdictions.csv').open(encoding='utf-8-sig',newline='') as f:required={r['jurisdiction_id'] for r in csv.DictReader(f)}
    with args.queue.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    ids=[r['jurisdiction_id'] for r in rows]
    if len(set(ids))!=len(ids) or set(ids)!=required:raise ValueError('Audit queue must equal authoritative inventory exactly')
    verified=[];pending=[]
    for row in rows:
        try:
            if row['status']!='verified' or not reviewed({'reviewed_by':row['reviewer'],'reviewed_at':row['reviewed_at']}):raise ValueError('Review absent')
            audit=read_json(artifact_path(ROOT,{'path':row['source_audit_path'],'sha256':row['source_audit_sha256']}));check_source_audit(ROOT,audit)
            if row['jurisdiction_id'] not in audit['territory_ids']:raise ValueError('Source does not cover jurisdiction')
            verified.append(row['jurisdiction_id'])
        except (ValueError,KeyError,TypeError,OSError):pending.append(row['jurisdiction_id'])
    report={'status':'passed' if not pending else 'blocked','required':len(required),'verified':len(verified),'pending':len(pending),'pending_ids':pending,'limitations':['Structural/hash check cannot authenticate reviewer expertise, normative completeness or institutional inventory correctness. No database coverage flags are changed.']}
    (ROOT/'verification/reports/coverage-queue-check.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Coverage audit check: {len(verified)} verified, {len(pending)} pending.')
    return int(bool(pending))


if __name__=='__main__':raise SystemExit(main())
