import hashlib
import json
import httpx
import pytest
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.model_integrity import verify_artifacts


async def test_body_limit_applies_before_multipart_parsing():
    app=create_app(Settings(upload_max_bytes=1024),connect=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
        response=await client.post("/v1/documents",content=b"PRIVATE_CANARY"*10000,
                                   headers={"Content-Type":"multipart/form-data; boundary=x"})
        assert response.status_code==413
        assert "PRIVATE_CANARY" not in response.text
        async def chunks():
            for _ in range(80):yield b"x"*1024
        response=await client.post("/v1/documents",content=chunks())
        assert response.status_code==413


def test_model_integrity_fails_on_revision_hash_and_path(tmp_path):
    artifact=tmp_path/"weights.bin"
    artifact.write_bytes(b"known weights")
    entry={"revision":"a"*40,"files":{"weights.bin":hashlib.sha256(artifact.read_bytes()).hexdigest()}}
    verify_artifacts(tmp_path,entry,"a"*40)
    artifact.write_bytes(b"tampered")
    with pytest.raises(ValueError):verify_artifacts(tmp_path,entry,"a"*40)
    with pytest.raises(ValueError):verify_artifacts(tmp_path,entry,"b"*40)
    entry["files"]={"../outside":"0"*64}
    with pytest.raises(ValueError):verify_artifacts(tmp_path,entry,"a"*40)


@pytest.mark.parametrize("url",["https://example.org","http://8.8.8.8","http://127.0.0.1@example.org","http://169.254.169.254"])
def test_laya_endpoint_cannot_send_private_context_outside_local_boundary(url):
    with pytest.raises(ValueError):Settings(_env_file=None,laya_base_url=url)
