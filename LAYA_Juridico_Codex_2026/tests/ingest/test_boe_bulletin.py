from pathlib import Path
from services.ingest.ingest.boe_bulletin import parse_summary

def test_real_summaries_include_administrative_and_business_items():
    folder=Path('tests/fixtures/bulletins')
    boe=parse_summary((folder/'boe-20251010.xml').read_bytes(),'boe')
    borme=parse_summary((folder/'borme-20251010.xml').read_bytes(),'borme')
    assert any(item['normative'] for item in boe['items'])
    assert any(not item['normative'] for item in boe['items'])
    assert borme['items'] and not any(item['normative'] for item in borme['items'])
    assert all(item['pdf_url'].startswith('https://www.boe.es/') for item in boe['items']+borme['items'])
    assert boe['date'].isoformat()=='2025-10-10'
