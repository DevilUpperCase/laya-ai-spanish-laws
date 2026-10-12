"""Collect public-only holdout rankings after a reviewed policy is sealed."""
import argparse,hashlib,json,math,sys,time
from datetime import datetime,timezone
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.metrics import validate_reviewed_dataset


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=Path,required=True);p.add_argument('--policy',type=Path,required=True);p.add_argument('--policy-sha256',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--public-cases',action='store_true',required=True,help='Attest that queries are public evaluation cases, without private client content')
    args=p.parse_args()
    if args.output.exists() or sha(args.policy)!=args.policy_sha256:raise ValueError('New output and matching independently recorded policy hash required')
    policy=json.loads(args.policy.read_text());cases=validate_reviewed_dataset(json.loads(args.cases.read_text(encoding='utf-8')))
    if policy.get('cases_sha256')!=sha(args.cases) or not policy.get('freeze_evidence_sha256') or not policy.get('frozen_at'):raise ValueError('Reviewed dataset and sealed policy required before holdout collection')
    session=json.loads((ROOT/'private-data/local-session.json').read_text());rankings={};observations=[]
    with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+session['token'],'X-Tenant-ID':session['tenant_id']},timeout=180,trust_env=False) as client:
        for case in cases:
            payload={'query':case['query'],'territory_codes':case.get('territory_codes',[])}
            if case.get('as_of'):payload['as_of']=case['as_of']
            start=time.perf_counter();response=client.post('/v1/search',json=payload)
            if response.status_code!=200:raise RuntimeError('Holdout request failed; do not treat errors as empty negative rankings')
            body=response.json();rankings[case['id']]=list(dict.fromkeys(result['section_version_id'] for result in body['results']))
            observations.append({'id':case['id'],'ms':round((time.perf_counter()-start)*1000,2),'engines':body['engines'],'warnings':body['warnings']})
            print(f'Collected {len(rankings)}/{len(cases)} public holdout cases.',flush=True)
    times=sorted(row['ms'] for row in observations)
    args.output.write_text(json.dumps(rankings,indent=2)+'\n')
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'collected_requires_quality_and_professional_review','cases_sha256':sha(args.cases),'policy_sha256':sha(args.policy),'rankings_sha256':sha(args.output),'p95_ms':times[math.ceil(len(times)*.95)-1],'error_rate':0.0,'requests':observations,'limitations':['Section-version rankings deduplicate passages by first occurrence. No professional provenance/date review or LAYA ranking activation is implied.','An operator-supplied policy hash must come from independent pre-holdout custody; this tool cannot authenticate that custody.']}
    args.output.with_suffix('.observations.json').write_text(json.dumps(report,indent=2)+'\n');print('Holdout rankings and measured observations saved.')


if __name__=='__main__':main()
