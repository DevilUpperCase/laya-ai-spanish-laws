from pathlib import Path
import json
from datetime import date
from services.ingest.ingest.dogc import parse_akoma


def test_missing_official_translation_does_not_discard_available_text():
    from services.ingest.ingest.dogc import DOGCAdapter
    from services.ingest.ingest.contracts import PublicationRef,RawPublication
    folder=Path(__file__).parents[2]/'sources/snapshots/dogc';row=json.loads((folder/'sample.json').read_text(encoding='utf-8'))[0]
    raw=RawPublication(PublicationRef('DOGC_NORMATIVE','DOGC-'+row['n_mero_de_control'],row['format_html']['url'],date(2026,7,9)),json.dumps({'metadata':row,'documents':{'ca':(folder/'sample-cat.xml').read_text(encoding='utf-8'),'es':''}}).encode(),'json')
    adapter=DOGCAdapter()
    try:
        parsed=adapter.parse(raw)
        assert parsed.versions and all(v.language_code=='ca' for v in parsed.versions)
        assert 'OFFICIAL_TRANSLATION_MISSING' in parsed.ingestion_warnings
    finally:adapter.close()


def test_actual_dogc_document_preserves_language_and_unknown_effectiveness():
    folder=Path(__file__).parents[2]/'sources/snapshots/dogc'
    row=json.loads((folder/'sample.json').read_text(encoding='utf-8'))[0]
    versions,warnings=parse_akoma((folder/'sample-cat.xml').read_bytes(),row,'ca')
    assert versions and any('Decret' in v.text for v in versions)
    assert all(v.language_code=='ca' and v.publication_date==date(2026,7,9) and not v.effectiveness_verified for v in versions)
    assert 'OFFICIAL_ANNEXES_NOT_INDEXED' in warnings
    assert len({v.id for v in versions})==len(versions)


def test_known_publications_do_not_break_catalogue_pagination():
    adapter=__import__('services.ingest.ingest.dogc',fromlist=['DOGCAdapter']).DOGCAdapter(page_size=1)
    row={'n_mero_de_control':'0000-81','data_de_publicaci_del_diari':'1981-11-06T00:00:00'}
    class Response:
        def json(self):return [row]
    adapter.known_ids={'DOGC-0000-81'};adapter.http.get=lambda *args:Response()
    try:
        page=adapter.discover();assert not page.publications and page.next_cursor=={'offset':1}
    finally:adapter.close()
