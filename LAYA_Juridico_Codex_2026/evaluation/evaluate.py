"""Evaluate recorded public-corpus rankings against reviewed, sealed holdout data."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from .metrics import ranking_metrics,validate_reviewed_dataset,negative_rate,quality_passes,positive_strata


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases",type=Path,required=True)
    parser.add_argument("--rankings",type=Path,required=True)
    parser.add_argument("--frozen-policy",type=Path,required=True)
    parser.add_argument("--policy-sha256",required=True,help="Independent pre-holdout policy receipt hash")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if sha(args.frozen_policy)!=args.policy_sha256:raise ValueError("Policy changed after freeze receipt")
    policy=json.loads(args.frozen_policy.read_text())
    if policy.get("cases_sha256")!=sha(args.cases) or not policy.get("freeze_evidence_sha256"):
        raise ValueError("Reviewed dataset/freeze evidence missing or changed")
    cases=validate_reviewed_dataset(json.loads(args.cases.read_text()))
    rankings=json.loads(args.rankings.read_text())
    if set(rankings)!={c["id"] for c in cases}:raise ValueError("Rankings must match holdout IDs exactly")
    metrics={key:[] for key in ("recall20","mrr10","ndcg10","precision5")}
    pairs=[]
    for case in cases:
        rank=rankings[case["id"]]
        r20=ranking_metrics(rank,case["judgments"],20)
        r10=ranking_metrics(rank,case["judgments"],10)
        r5=ranking_metrics(rank,case["judgments"],5)
        values={"recall20":r20["recall"],"mrr10":r10["mrr"],"ndcg10":r10["ndcg"],"precision5":r5["precision"]}
        if case.get("negative") is not True:
            for key,value in values.items():metrics[key].append(value)
        pairs.append((case,values))
    if not all(metrics.values()):raise ValueError("Positive holdout cases required")
    averages={key:sum(values)/len(values) for key,values in metrics.items()}
    thresholds=policy.get("minimums",{})
    if not {"recall20","mrr10","ndcg10","precision5"}.issubset(thresholds) or any(type(v) not in {float,int} or not math.isfinite(v) or not 0<=v<=1 for v in thresholds.values()):
        raise ValueError("Frozen numeric minimums required")
    strata=positive_strata(pairs)
    required_strata={c['language'] for c in cases}|{c['tier'] for c in cases}
    if set(strata)!=required_strata:raise ValueError('Positive cases required in every language/tier stratum')
    stratum_minimums=policy.get("stratum_minimums",{})
    if set(stratum_minimums)!=set(strata):raise ValueError("Frozen stratum minimums required")
    averages["negative_false_positive_rate"]=negative_rate(cases,rankings)
    passed=quality_passes(averages,thresholds,policy.get("maximum_negative_false_positive_rate"))
    stratum_scores={name:{key:sum(row[key] for row in values)/len(values) for key in metrics} for name,values in strata.items()}
    for name,minimums in stratum_minimums.items():
        if set(minimums)!={"recall20","mrr10","ndcg10","precision5"}:raise ValueError("Stratum metrics incomplete")
        for key,threshold in minimums.items():
            if type(threshold) not in {float,int} or not math.isfinite(threshold) or not 0<=threshold<=1:raise ValueError("Invalid stratum minimum")
            passed &= stratum_scores[name][key]>=threshold
    report={"status":"metrics_passed" if passed else "failed","holdout_count":len(cases),"metrics":averages,"strata":stratum_scores,
            "cases_sha256":sha(args.cases),"policy_sha256":sha(args.frozen_policy),
            "limitation":"Does not authenticate reviewers, prove source/provenance accuracy, performance, or authorize LAYA ranking."}
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    return 0 if passed else 1


if __name__=="__main__":raise SystemExit(main())
