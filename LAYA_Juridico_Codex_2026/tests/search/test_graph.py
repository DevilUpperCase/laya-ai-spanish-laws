import pytest
from uuid import uuid4
from services.api.app.contracts import SearchRequest, TenantContext, Candidate, RetrievalQuery
from services.api.app.search_graph import build_search_graph
from services.api.app.fusion import fuse
from services.api.app.explanations import build_reasons
from langchain_core.runnables import RunnableLambda


def candidate(identifier="a"):
    return Candidate(candidate_id=identifier, instrument_id="i", section_version_id="v", heading="Artículo 2",
                     passage="Un arrendamiento de vivienda.", language_code="es", jurisdiction_code="ES",
                     official_reference="29/1994", official_url="https://www.boe.es/", publication_date="1994-11-25",
                     source_id="BOE", start_offset=0, end_offset=28, version_ref="original")


def test_deduped_rrf_and_original_spans():
    assert fuse([["a", "a", "b"], ["b"]])[0][0] == "b"
    c = candidate()
    reasons = build_reasons("VIVIENDA", c)
    match = next(r for r in reasons if r.kind == "literal_overlap")
    e = match.evidence
    assert c.passage[e["passage_start"]:e["passage_end"]] == "vivienda"
    assert not c.effectiveness_verified


@pytest.mark.asyncio
async def test_actual_graph_shadow_failure_keeps_order_and_no_persistence():
    calls = []
    async def retrieve(query):
        calls.append("retrieve")
        return [candidate("a"), candidate("b")]
    class Laya:
        async def classify(self, query, candidates):
            calls.append("laya")
            raise TimeoutError()
    graph = build_search_graph(RunnableLambda(retrieve), Laya(), build_reasons)
    assert graph.checkpointer is None
    context = TenantContext(user_id=uuid4(), tenant_id=uuid4(), role="lawyer")
    q = RetrievalQuery(query="vivienda", request=SearchRequest(query="vivienda"), context=context, trace_id="test")
    state = await graph.ainvoke({"retrieval_query": q, "warnings": []}, config={"callbacks": [], "recursion_limit": 12})
    assert calls == ["retrieve", "laya"]
    assert [r.candidate_id for r in state["results"]] == ["a", "b"]
    assert "LAYA_DEGRADED" in state["warnings"]


@pytest.mark.asyncio
async def test_empty_candidates_skip_laya():
    class Laya:
        async def classify(self, *args):
            raise AssertionError("Must not run on empty corpus")
    graph = build_search_graph(RunnableLambda(lambda _: []), Laya(), build_reasons)
    q = RetrievalQuery(query="x", request=SearchRequest(query="x"), context=TenantContext(user_id=uuid4(), tenant_id=uuid4(), role="reader"), trace_id="t")
    state = await graph.ainvoke({"retrieval_query": q, "warnings": []})
    assert state["results"] == []
    assert state["laya_status"] == "empty"
