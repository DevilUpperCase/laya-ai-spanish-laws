def apply_laya_policy(candidates, decisions, mode="shadow"):
    if mode != "shadow":
        raise ValueError("Ranking activation requires a separately approved evaluation")
    warnings=[]
    if [d.candidate_id for d in decisions] != [c.candidate_id for c in candidates]:
        warnings.append("LAYA_DEGRADED")
    elif any(d.truncated is not False or d.abstained is not False for d in decisions):
        warnings.append("LAYA_INCOMPLETE")
    return candidates,warnings
