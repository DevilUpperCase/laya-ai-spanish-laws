import pytest
from fastapi.testclient import TestClient
from services.api.app.config import Settings
from services.api.app.contracts import SearchRequest, DocumentSelection
from services.api.app.main import create_app


def test_required_stack_and_fail_closed_config():
    import langchain_core
    import langgraph.graph
    assert langchain_core and langgraph.graph
    with pytest.raises(ValueError):
        Settings(app_env="production",_env_file=None)
    with TestClient(create_app(Settings(), connect=False)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").status_code == 401
        assert client.post("/v1/search", json={"query": "arrendamiento"}).status_code == 401


def test_search_contract_rejects_invalid_private_context():
    with pytest.raises(ValueError):
        SearchRequest(query="x", tenant_id="client supplied")
    with pytest.raises(ValueError):
        SearchRequest(mode="document", query="x")
    with pytest.raises(ValueError):
        SearchRequest(query="x", selection=DocumentSelection(page_number=1, start_offset=2, end_offset=3))
