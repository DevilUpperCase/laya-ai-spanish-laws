import pytest
import httpx
from services.api.app.config import Settings
from services.api.app.laya_client import LayaClient
from tests.search.test_graph import candidate


@pytest.mark.models
async def test_real_local_laya_authenticated_inference():
    settings=Settings()
    async with httpx.AsyncClient(base_url=settings.laya_base_url,trust_env=False,timeout=30) as client:
        assert (await client.post("/v1/systemone",json={"state":"public readiness","questions":{}})).status_code==401
        health=await client.get("/health",headers={"Authorization":"Bearer "+settings.laya_api_key})
        assert health.json()["revisions"]["juridico"]==settings.laya_model_revision
    # Readiness fixture is synthetic, never a fabricated legal corpus record.
    local=LayaClient(settings.model_copy(update={"laya_timeout_seconds":30}))
    decision=(await local.classify("arrendamiento de vivienda",[candidate()]))[0]
    assert decision.model_revision==settings.laya_model_revision
    assert decision.label in {"none","partial","direct"}
    assert decision.truncated is False
    await local.close()
