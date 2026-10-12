"""Seal a professionally accepted policy before collecting holdout rankings."""
import argparse,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
from evaluation.metrics import validate_reviewed_dataset,quality_passes


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cases','proposal','pilot','review-evidence','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reviewer',required=True);args=p.parse_args()
    if not args.reviewer.strip() or args.output.exists():raise ValueError('Named reviewer and a new output path required')
    cases=validate_reviewed_dataset(json.loads(args.cases.read_text(encoding='utf-8')))
    policy=json.loads(args.proposal.read_text());pilot=json.loads(args.pilot.read_text())
    if pilot.get('status')!='measured_not_frozen' or not pilot.get('requests') or pilot.get('error_rate')!=0:raise ValueError('Successful measured hardware pilot required')
    quality_passes({**policy['minimums'],'negative_false_positive_rate':0},policy['minimums'],policy['maximum_negative_false_positive_rate'])
    strata={c['language'] for c in cases}|{c['tier'] for c in cases}
    if set(policy.get('stratum_minimums',{}))!=strata:raise ValueError('All language/tier minimums required')
    for values in policy['stratum_minimums'].values():quality_passes({**values,'negative_false_positive_rate':0},values,0)
    if not math.isfinite(policy.get('maximum_p95_ms',float('nan'))) or policy['maximum_p95_ms']<=0:raise ValueError('Finite positive performance limit required')
    if not args.review_evidence.is_file() or args.review_evidence.stat().st_size==0:raise ValueError('Professional acceptance evidence required')
    policy.update({'cases_sha256':sha(args.cases),'freeze_evidence_sha256':sha(args.review_evidence),'pilot_sha256':sha(args.pilot),'frozen_by':args.reviewer,'frozen_at':datetime.now(timezone.utc).isoformat(),'status':'frozen_requires_independent_receipt'})
    args.output.write_text(json.dumps(policy,indent=2)+'\n')
    receipt={'policy_sha256':sha(args.output),'frozen_at':policy['frozen_at'],'frozen_by':args.reviewer,'limitations':'Copy this receipt to independent immutable custody before running holdout queries. This tool validates structure and hashes, not reviewer identity or legal expertise.'}
    args.output.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Frozen policy and independent-custody receipt created.')


if __name__=='__main__':main()
