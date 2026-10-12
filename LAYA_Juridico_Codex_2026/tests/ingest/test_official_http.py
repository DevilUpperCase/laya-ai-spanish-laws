import gzip
import httpx,pytest
from services.ingest.ingest.official_http import OfficialHTTP


def test_compressed_public_response_is_decoded_once_and_bounded():
    c=OfficialHTTP({'official.invalid'},max_bytes=20)
    c.client.close();c.client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,headers={'Content-Encoding':'gzip'},content=gzip.compress(b'legal text'))))
    try:assert c.get('https://official.invalid/data').content==b'legal text'
    finally:c.close()


def test_official_redirect_cannot_leave_host_allowlist():
    c=OfficialHTTP({'official.invalid'})
    c.client.close();c.client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(302,headers={'Location':'http://127.0.0.1/private'})))
    try:
        with pytest.raises(ValueError):c.get('https://official.invalid/data')
    finally:c.close()
