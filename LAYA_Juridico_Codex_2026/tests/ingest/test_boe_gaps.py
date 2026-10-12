from pathlib import Path
from datetime import date
from types import SimpleNamespace
import pytest
from services.ingest.ingest.boe import BOEAdapter
from services.ingest.ingest.jurisdiction_resolver import region_resolver

FOLDER=Path(__file__).parents[1]/'fixtures/boe/gaps'


def test_baleares_historical_name_is_exact_alias_without_fuzzy_issuer_mapping():
    resolve=region_resolver([{'id':'ES-AUTO-04','level':'autonomous_community','name':'Balears, Illes'}])
    assert resolve(SimpleNamespace(scope='Autonómico',issuer='Comunidad Autónoma de las Islas Baleares'))=='ES-AUTO-04'
    assert resolve(SimpleNamespace(scope='Autonómico',issuer='Consejería de Islas Baleares')) is None


def test_unknown_effective_date_remains_unknown():
    p=BOEAdapter.parse_xml((FOLDER/'BOE-A-1964-7544.xml').read_bytes(),'https://www.boe.es/data')
    assert any(v.effective_from is None for v in p.versions)


@pytest.mark.parametrize('identifier,norm,expected',[('BOE-A-2010-8228','BOE-A-2012-8745',date(2012,6,30)),('BOE-A-1993-4684','BOE-A-1996-11609',date(1996,5,24))])
def test_invalid_version_publication_requires_correlated_official_evidence(identifier,norm,expected):
    content=(FOLDER/(identifier+'.xml')).read_bytes()
    with pytest.raises(ValueError):BOEAdapter.parse_xml(content,'https://www.boe.es/data')
    p=BOEAdapter.parse_xml(content,'https://www.boe.es/data',publication_dates={norm:expected})
    assert any(v.version_ref.startswith(norm+':') and v.publication_date==expected for v in p.versions)
