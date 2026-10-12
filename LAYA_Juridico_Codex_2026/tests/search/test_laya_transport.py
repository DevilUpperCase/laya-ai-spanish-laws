import httpx
import pytest
from services.api.app.laya_client import LayaClient
from services.api.app.config import Settings
from tests.search.test_graph import candidate


def reply(truncated=False):
    return {"answers":{"relevance":{"type":"choice","choice":"direct","probabilities":{"none":0.1,"partial":0.2,"direct":0.7},"answer_confidence":0.7,"abstention":"passed"}},"usage":{"truncated":truncated,"output_tokens":0}}


@pytest.mark.asyncio
async def test_http_batch_shape_and_full_metadata():
    async def handle(request):
        import json
        body=json.loads(request.content)
        assert "states" in body and "questions" in body and "requests" not in body
        assert request.headers["Authorization"] == "Bearer testsecret"
        return httpx.Response(200,json={"results":[reply(),reply()]})
    client=LayaClient(Settings(laya_api_key="testsecret",laya_model_revision="a"*40),transport=httpx.MockTransport(handle))
    decisions=await client.classify("vivienda",[candidate("a"),candidate("b")])
    assert [d.candidate_id for d in decisions] == ["a","b"]
    assert decisions[0].truncated is False
    assert decisions[0].abstained is False
    await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad",[{}, {"results":[]}, {"results":[reply(),reply()]}, {"results":[{**reply(),"answers":{"relevance":{"choice":"direct","probabilities":{"none":-1,"partial":1,"direct":1}}}}]}])
async def test_malformed_cardinality_probability_rejected(bad):
    c=LayaClient(Settings(laya_api_key="x"),transport=httpx.MockTransport(lambda _:httpx.Response(200,json=bad)))
    with pytest.raises(RuntimeError):
        await c.classify("x",[candidate()])
    await c.close()


@pytest.mark.asyncio
async def test_missing_truncation_unknown_and_circuit_opens():
    data=reply()
    data["usage"].pop("truncated")
    c=LayaClient(Settings(laya_api_key="x"),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={"results":[data]})))
    assert (await c.classify("x",[candidate()]))[0].truncated is None
    await c.close()


@pytest.mark.parametrize("bad",[{"answers":{"relevance":None},"usage":{}},{"answers":{"relevance":{}},"usage":None},{"answers":[],"usage":{}},None])
async def test_null_nested_response_is_degraded(bad):
    c=LayaClient(Settings(laya_api_key="x"),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={"results":[bad]})))
    try:
        with pytest.raises(RuntimeError):await c.classify("x",[candidate()])
    finally:await c.close()
    count=0
    async def fail(_):
        nonlocal count
        count+=1
        return httpx.Response(503)
    c=LayaClient(Settings(laya_api_key="x",laya_circuit_failures=1),transport=httpx.MockTransport(fail))
    with pytest.raises(RuntimeError): await c.classify("x",[candidate()])
    previous=count
    with pytest.raises(RuntimeError): await c.classify("x",[candidate()])
    assert count==previous
    await c.close()
