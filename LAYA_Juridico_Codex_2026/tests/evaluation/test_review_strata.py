from evaluation.prepare_review import drafts
from evaluation.metrics import positive_strata,validate_reviewed_dataset
import pytest


def test_draft_queue_cannot_pass_professional_acceptance():
    rows=drafts();assert len(rows)==200
    assert len({(c['language'],c['tier']) for c in rows})==20
    with pytest.raises(ValueError,match='professional review'):validate_reviewed_dataset(rows)


def test_negative_cases_do_not_dilute_positive_stratum_quality():
    pairs=[({'language':'es','tier':'state','negative':False},{'recall20':1.0}),({'language':'es','tier':'state','negative':True},{'recall20':0.0})]
    assert positive_strata(pairs)=={'es':[{'recall20':1.0}],'state':[{'recall20':1.0}]}
