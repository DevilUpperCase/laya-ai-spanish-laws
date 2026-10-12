from pathlib import Path
from services.ingest.ingest.boe import BOEAdapter

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/boe/BOE-A-1994-26003.xml"


def test_version_history_preserved_and_publication_not_effective():
    parsed = BOEAdapter.parse_xml(FIXTURE.read_bytes(), "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-1994-26003")
    assert parsed.external_id == "BOE-A-1994-26003"
    assert "Arrendamientos Urbanos" in parsed.title
    assert len([v for v in parsed.versions if v.section_key == "a2"]) > 1
    assert any(v.publication_date != v.effective_from for v in parsed.versions)
    assert all(not v.effectiveness_verified for v in parsed.versions)
    assert len({v.id for v in parsed.versions}) == len(parsed.versions)
    assert parsed.official_url.startswith("https://www.boe.es/")


def test_replayed_parse_is_stable():
    first = BOEAdapter.parse_xml(FIXTURE.read_bytes(), "https://www.boe.es/data")
    second = BOEAdapter.parse_xml(FIXTURE.read_bytes(), "https://www.boe.es/data")
    assert first == second


def test_hostile_xml_rejected():
    import pytest
    with pytest.raises(Exception):
        BOEAdapter.parse_xml(b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><response>&xxe;</response>', "https://www.boe.es/data")
