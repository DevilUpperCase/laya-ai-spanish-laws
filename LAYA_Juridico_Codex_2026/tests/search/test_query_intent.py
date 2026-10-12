from services.api.app.contracts import SearchRequest
from services.api.app.query_intent import build_query_plan,split_passages

def test_intent_preserves_original_reference_and_filters():
    request=SearchRequest(query='What protects a tenant under BOE-A-1994-26003?',intent={'issue':'Lease termination','objective':'Challenge eviction'},territory_codes=['ES'],as_of='2020-01-01')
    plan=build_query_plan(request)
    assert plan['inputs'][0]==request.query
    assert plan['territory_codes']==['ES'] and str(plan['as_of'])=='2020-01-01'
    assert any('Lease termination' in item for item in plan['inputs'])
    assert len(plan['inputs'])<=4

def test_passages_keep_exact_unicode_offsets():
    text='😀áñ'+('lease clause '*200)
    chunks=split_passages(text)
    assert len(chunks)>1
    for start,end,passage in chunks:assert text[start:end]==passage and end-start<=1000
