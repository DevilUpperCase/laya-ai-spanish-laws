import math
import re


def positive_strata(pairs):
    """Positive relevance scores and negative false positives have separate denominators."""
    strata={}
    for case,values in pairs:
        if case.get('negative') is True:continue
        for name in (case['language'],case['tier']):strata.setdefault(name,[]).append(values)
    return strata


def ranking_metrics(ranked,judgments,k=10):
    if k<=0 or len(set(ranked))!=len(ranked):raise ValueError("Invalid ranking")
    if any(type(g) is not int or not 0<=g<=3 for g in judgments.values()):raise ValueError("Invalid relevance grade")
    relevant={key for key,grade in judgments.items() if grade>0}
    selected=ranked[:k]
    hits=[i for i,key in enumerate(selected,1) if key in relevant]
    def dcg(grades):return sum((2**grade-1)/math.log2(i+2) for i,grade in enumerate(grades))
    ideal=dcg(sorted(judgments.values(),reverse=True)[:k])
    return {"recall":len(hits)/len(relevant) if relevant else 0,
            "precision":len(hits)/k,"mrr":1/hits[0] if hits else 0,
            "ndcg":dcg([judgments.get(key,0) for key in selected])/ideal if ideal else 0,
            "false_positive":int(not relevant and bool(selected))}


def validate_reviewed_dataset(cases):
    if len(cases)<200:raise ValueError("At least 200 professionally reviewed cases required")
    ids=[c["id"] for c in cases]
    if len(set(ids))!=len(ids):raise ValueError("Duplicate case IDs")
    for case in cases:
        reviewer=case.get('reviewer');evidence=case.get('review_evidence_sha256')
        if not isinstance(reviewer,str) or not reviewer.strip() or not isinstance(evidence,str) or not re.fullmatch(r"[0-9a-f]{64}",evidence):
            raise ValueError("Named professional review evidence required")
        if case.get("split") not in {"calibration","holdout"}:raise ValueError("Disjoint calibration/holdout split required")
        ranking_metrics([],case["judgments"])
        if case.get("negative") is True and any(case["judgments"].values()):raise ValueError("Negative case has positive judgments")
    holdout=[c for c in cases if c["split"]=="holdout"]
    if not any(c["split"]=="calibration" for c in cases) or not holdout:raise ValueError("Both evaluation splits required")
    if not {"es","ca","gl","eu"}.issubset(c["language"] for c in holdout):raise ValueError("Holdout languages incomplete")
    if not {"state","regional","provincial","municipal","island_foral"}.issubset(c["tier"] for c in holdout):raise ValueError("Holdout territorial tiers incomplete")
    if not any(c.get("temporal") is True for c in holdout) or not any(c.get("negative") is True for c in holdout):raise ValueError("Temporal/negative holdout cases required")
    return holdout


def negative_rate(cases,rankings):
    negative=[c for c in cases if c.get("negative") is True]
    if not negative:raise ValueError("Negative holdout cases required")
    return sum(bool(rankings[c["id"]]) for c in negative)/len(negative)


def quality_passes(scores,minimums,maximum_negative_rate):
    if set(minimums)!={"recall20","mrr10","ndcg10","precision5"}:raise ValueError("Invalid minimum metric names")
    values=[*minimums.values(),maximum_negative_rate]
    if any(type(v) not in {float,int} or not math.isfinite(v) or not 0<=v<=1 for v in values):raise ValueError("Finite numeric thresholds required")
    return all(scores[key]>=threshold for key,threshold in minimums.items()) and scores["negative_false_positive_rate"]<=maximum_negative_rate
