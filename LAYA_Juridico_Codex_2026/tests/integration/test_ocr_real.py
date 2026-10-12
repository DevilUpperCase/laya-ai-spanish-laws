from pathlib import Path
import pymupdf
import pytest
from services.api.app.config import ROOT
from services.api.app.documents import extract_pages


@pytest.mark.models
def test_actual_local_ocr_on_image_only_pdf(monkeypatch):
    monkeypatch.setenv("TESSDATA_PREFIX",str(ROOT/"model-cache/ocr"))
    source=pymupdf.open()
    source.new_page().insert_text((50,100),"Contrato de arrendamiento de vivienda",fontsize=20)
    image=source[0].get_pixmap(dpi=200,alpha=False)
    scanned=pymupdf.open()
    page=scanned.new_page()
    page.insert_image(page.rect,stream=image.tobytes("png"))
    assert not page.get_text().strip()
    pages=extract_pages(scanned.tobytes(),"application/pdf",300,2_000_000,ocr=True)
    assert "vivienda" in pages[0]["text"].casefold()
    assert pages[0]["ocr_uncertain"] is True
