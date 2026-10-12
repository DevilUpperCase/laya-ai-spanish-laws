import pytest
from evaluation.metrics import ranking_metrics,validate_reviewed_dataset


def test_hand_calculated_metrics_and_negative_case():
    result=ranking_metrics(["irrelevant","b","a"],{"a":3,"b":1},k=3)
    assert result["recall"]==1
    assert result["mrr"]==0.5
    assert result["precision"]==pytest.approx(2/3)
    assert 0<result["ndcg"]<1
    assert ranking_metrics([],{},k=5)["false_positive"]==0
    assert ranking_metrics(["a"],{},k=5)["false_positive"]==1
    with pytest.raises(ValueError):ranking_metrics(["a","a"],{"a":3})


def test_professional_dataset_cannot_be_fabricated_from_empty_or_duplicate_cases():
    with pytest.raises(ValueError):validate_reviewed_dataset([])
    case={"id":"one","language":"es","tier":"state","split":"holdout","judgments":{},
          "negative":True,"temporal":False,"reviewer":"Named reviewer","review_evidence_sha256":"a"*64}
    with pytest.raises(ValueError):validate_reviewed_dataset([case]*200)
