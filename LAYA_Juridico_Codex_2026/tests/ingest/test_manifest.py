import hashlib,json
import pytest


def test_manifest_requires_real_review_artifact_and_exact_host(tmp_path):
    from services.ingest.ingest.manifest import load_manifest
    review=tmp_path/'review.md';review.write_text('Synthetic review fixture, not release approval')
    data={'source_id':'TEST_OFFICIAL','name':'Fixture','official_url':'https://official.example/','terms_url':'https://official.example/terms','allowed_hosts':['official.example'],'reviewer':'Synthetic fixture','review_evidence':'review.md','review_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),'publications':[{'external_id':'1','official_url':'https://evil.example/1','title':'Regulation','publication_date':'2026-01-01','jurisdiction_id':'ES','language':'es','legal_type':'Reglamento','normative':True,'format':'html','selector':'article'}]}
    path=tmp_path/'manifest.json';path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='host'):load_manifest(path,tmp_path)
    data['publications'][0]['official_url']='https://official.example/1';data['publications'][0]['normative']=False;path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='normative'):load_manifest(path,tmp_path)
    data['publications'][0]['normative']=True;path.write_text(json.dumps(data))
    result=load_manifest(path,tmp_path);assert len(result['publications'])==1
    review.write_text('Changed')
    with pytest.raises(ValueError,match='review'):load_manifest(path,tmp_path)


def test_manifest_pdf_uses_real_bounded_pdf_worker(monkeypatch):
    import pymupdf
    from datetime import date
    from services.api.app.config import Settings
    from services.ingest.ingest.manifest import ManifestAdapter
    from services.ingest.ingest.contracts import PublicationRef,RawPublication
    # Scanner transport is verified separately with EICAR; this fixture isolates parser wiring.
    monkeypatch.setattr('services.api.app.documents.scan_upload',lambda *args:True)
    row={'external_id':'same-id','official_url':'https://official.example/norm','publication_date':'2026-01-01','title':'Synthetic regulation','legal_type':'Reglamento','language':'es','format':'pdf'}
    adapter=ManifestAdapter({'source_id':'TEST_OFFICIAL','allowed_hosts':['official.example'],'publications':[row]},Settings())
    try:
        pdf=pymupdf.open();pdf.new_page().insert_text((72,72),'SYNTHETIC normative parser test.');content=pdf.tobytes();pdf.close()
        parsed=adapter.parse(RawPublication(PublicationRef(adapter.source_id,'0',row['official_url'],date(2026,1,1)),content,'pdf'))
        assert 'SYNTHETIC normative' in parsed.versions[0].text
        assert parsed.versions[0].effective_from is None and parsed.instrument_id.startswith('TEST_OFFICIAL:')
        assert parsed.external_id=='same-id' and not parsed.is_consolidated
    finally:adapter.close()
