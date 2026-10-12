from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import pytest
import pymupdf
from docx import Document
from services.api.app.documents import validate_upload, extract_pages
from services.api.app.selection import resolve_span
from services.api.app.contracts import DocumentSelection
from services.api.app.errors import DomainError


def pdf_bytes(text="Private synthetic test, not legislation."):
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), text)
    return doc.tobytes()


def test_real_pdf_docx_and_unicode_selection():
    pdf = pdf_bytes()
    assert validate_upload(pdf,"application/pdf") == "application/pdf"
    pages = extract_pages(pdf,"application/pdf",300,2_000_000)
    assert "Private synthetic" in pages[0]["text"]
    document = Document()
    document.add_paragraph("A😀 jurídic català euskara galego")
    out = BytesIO()
    document.save(out)
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert validate_upload(out.getvalue(),mime) == mime
    text = extract_pages(out.getvalue(),mime,300,2_000_000)[0]["text"]
    assert resolve_span(text,DocumentSelection(page_number=1,start_offset=1,end_offset=2,selected_text="😀")) == "😀"
    with pytest.raises(DomainError):
        resolve_span(text,DocumentSelection(page_number=1,start_offset=1,end_offset=2,selected_text="X"))


def test_ocr_rejects_huge_page_before_rendering(monkeypatch):
    def must_not_render(*args,**kwargs):raise AssertionError("Oversized page rendered")
    monkeypatch.setattr(pymupdf.Page,"get_textpage_ocr",must_not_render)
    doc=pymupdf.open();doc.new_page(width=20000,height=20000)
    with pytest.raises(DomainError) as error:extract_pages(doc.tobytes(),"application/pdf",300,2_000_000,ocr=True)
    assert error.value.code=="DOCUMENT_LIMIT"


def test_mislabeled_and_zip_bombs_rejected():
    with pytest.raises(DomainError):
        validate_upload(pdf_bytes(),"text/plain")
    out = BytesIO()
    with ZipFile(out,"w",ZIP_DEFLATED) as z:
        z.writestr("word/document.xml",b"a"*2_000_000)
        z.writestr("[Content_Types].xml",b"types")
    with pytest.raises(DomainError):
        validate_upload(out.getvalue(),"application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def test_encrypted_pdf_rejected_and_empty_scan_is_explicit():
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256,owner_pw="secret",user_pw="secret")
    with pytest.raises(DomainError):
        extract_pages(data,"application/pdf",300,2_000_000)
    blank = pymupdf.open()
    blank.new_page()
    with pytest.raises(DomainError) as error:
        extract_pages(blank.tobytes(),"application/pdf",300,2_000_000)
    assert error.value.code == "OCR_REQUIRED"
