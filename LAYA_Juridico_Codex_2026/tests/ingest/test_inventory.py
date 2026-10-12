from pathlib import Path
from services.ingest.ingest.inventory import load_ine_snapshot


def test_official_inventory_has_unique_ids_and_valid_hierarchy():
    path=Path(__file__).resolve().parents[2]/"sources/snapshots"
    entities,limitations=load_ine_snapshot(path)
    ids={e["id"] for e in entities}
    assert len(ids)==len(entities)
    assert all(e["parent_id"] is None or e["parent_id"] in ids for e in entities)
    assert sum(e["level"]=="autonomous_community" for e in entities)==17
    assert sum(e["level"]=="autonomous_city" for e in entities)==2
    assert sum(e["level"]=="municipality" for e in entities)>8000
    assert any("island" in limitation.lower() for limitation in limitations)
    assert all(e["verified"] is False for e in entities)
    assert next(e["name"] for e in entities if e["id"]=="ES-MUN-17118")=="Palamós i Sant Joan"
    assert not any("creation/deletion" in l for l in limitations)


def test_regional_issuer_identity_is_exact_not_fuzzy():
    from types import SimpleNamespace
    from services.ingest.ingest.jurisdiction_resolver import region_resolver
    resolve=region_resolver([{"name":"Murcia, Región de","id":"ES-AUTO-14","level":"autonomous_community"}])
    assert resolve(SimpleNamespace(scope="Autonómico",issuer="Comunidad Autónoma de la Región de Murcia"))=="ES-AUTO-14"
    assert resolve(SimpleNamespace(scope="Autonómico",issuer="Consejería de salud de Murcia")) is None
