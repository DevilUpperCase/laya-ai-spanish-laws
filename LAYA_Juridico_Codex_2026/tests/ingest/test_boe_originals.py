import pytest
from services.ingest.ingest.boe_originals import pdf_url_from_xml

def test_only_original_metadata_pdf_is_accepted():
    xml=b'<documento><metadatos><identificador>BOE-A-1978-31229</identificador><url_pdf>/boe/dias/1978/12/29/pdfs/A29313-29424.pdf</url_pdf></metadatos></documento>'
    assert pdf_url_from_xml(xml,'BOE-A-1978-31229').startswith('https://www.boe.es/boe/dias/')
    with pytest.raises(ValueError):pdf_url_from_xml(xml,'BOE-A-2000-1')
    with pytest.raises(ValueError):pdf_url_from_xml(xml.replace(b'/boe/dias/',b'https://evil.test/'),'BOE-A-1978-31229')
