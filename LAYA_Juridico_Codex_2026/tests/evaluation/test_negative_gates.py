import pytest
from evaluation.metrics import negative_rate,quality_passes


def test_negative_rate_is_not_diluted_by_positive_cases():
    cases=[{"id":"bad","negative":True},{"id":"good","negative":True}]+[{"id":str(i),"negative":False} for i in range(100)]
    rankings={c["id"]:[] for c in cases};rankings["bad"]=["irrelevant"]
    assert negative_rate(cases,rankings)==0.5
    minimums={key:0 for key in ("recall20","mrr10","ndcg10","precision5")}
    scores={**minimums,"negative_false_positive_rate":0.5}
    assert not quality_passes(scores,minimums,0.1)
    assert quality_passes(scores,minimums,0.5)
    with pytest.raises(ValueError):quality_passes(scores,{**minimums,"false_positive":0.9},0.1)
