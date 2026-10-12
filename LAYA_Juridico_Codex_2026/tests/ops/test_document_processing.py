from datetime import datetime,timezone
from services.ingest.ingest.processing_status import completion_dimensions

def test_complete_finite_snapshot_cannot_pass_unknown_national_coverage():
    dimensions=completion_dimensions(expected=3,integrated=3,assets_missing=0,index_pending=0,national_verified=False,last_success=datetime.now(timezone.utc))
    assert dimensions['snapshot_processing']=='complete'
    assert dimensions['national_coverage']=='blocked'
    assert not dimensions['all_complete']
    unknown=completion_dimensions(expected=None,integrated=3,assets_missing=0,index_pending=0,national_verified=False,last_success=None)
    assert unknown['snapshot_processing']=='blocked' and unknown['freshness']=='stale'

def test_expanded_audit_requires_matching_scope_hash_and_review(tmp_path):
    import hashlib,json
    from services.ingest.ingest.processing_status import reviewed_all_publication_sources
    audit={'source_id':'TEST','scope':'all_publicly_accessible_official_bulletin_items','reviewer':'Synthetic validator fixture','reviewed_at':'2026-10-12',**{k:True for k in ('current_reconciled','available_history_reconciled','attachments_reconciled','subitems_reconciled')}}
    path=tmp_path/'audit.json';path.write_text(json.dumps(audit))
    scope={'audits':{'TEST':{'path':'audit.json','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}}
    assert reviewed_all_publication_sources(scope,tmp_path)=={'TEST'}
    audit['scope']='normative';path.write_text(json.dumps(audit))
    scope['audits']['TEST']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    assert reviewed_all_publication_sources(scope,tmp_path)==set()


def test_failed_or_unknown_period_blocks_matching_counts():
    dimensions=completion_dimensions(expected=3,integrated=3,assets_missing=0,index_pending=0,national_verified=True,last_success=datetime.now(timezone.utc),periods_complete=False)
    assert dimensions['snapshot_processing']=='blocked' and not dimensions['all_complete']
