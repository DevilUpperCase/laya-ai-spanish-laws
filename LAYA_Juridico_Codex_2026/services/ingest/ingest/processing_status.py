"""Independent processing, geographic coverage and freshness evidence."""
from datetime import datetime,timezone,timedelta
import hashlib
from pathlib import Path
import json

def reviewed_all_publication_sources(scope,root):
    """Hashes locate reviewed evidence; they do not authenticate a lawyer's judgment."""
    valid=set();root=Path(root).resolve()
    for source_id,entry in scope.get('audits',{}).items():
        try:
            path=(root/entry['path']).resolve()
            if not path.is_relative_to(root):continue
            content=path.read_bytes()
            if hashlib.sha256(content).hexdigest()!=entry['sha256']:continue
            audit=json.loads(content)
            if audit.get('source_id')!=source_id or audit.get('scope')!='all_publicly_accessible_official_bulletin_items':continue
            if not isinstance(audit.get('reviewer'),str) or not audit['reviewer'].strip() or not audit.get('reviewed_at'):continue
            if all(audit.get(k) is True for k in ('current_reconciled','available_history_reconciled','attachments_reconciled','subitems_reconciled')):valid.add(source_id)
        except (OSError,ValueError,KeyError,TypeError):continue
    return valid

def completion_dimensions(*,expected,integrated,assets_missing,index_pending,national_verified,last_success,now=None):
    now=now or datetime.now(timezone.utc)
    snapshot=expected is not None and expected==integrated and not assets_missing and not index_pending
    fresh=last_success is not None and now-timedelta(hours=36)<=last_success<=now+timedelta(minutes=5)
    return {'snapshot_processing':'complete' if snapshot else 'blocked','national_coverage':'verified' if national_verified else 'blocked',
            'freshness':'fresh' if fresh else 'stale','all_complete':bool(snapshot and fresh and national_verified)}

def collect_processing_status(conn,source_scope,*,now=None,verify_files=False,storage_root=None):
    now=now or datetime.now(timezone.utc)
    def number(sql):return conn.execute(sql).fetchone()[0]
    sources=conn.execute('SELECT id,adapter,audit_status,last_successful_sync FROM legal.sources ORDER BY id').fetchall()
    periods=conn.execute('''SELECT p.source_id,p.publication_date,p.expected_count,p.status,p.reconciled_at,
     (SELECT count(*) FROM legal.bulletin_items i WHERE i.source_id=p.source_id AND i.publication_date=p.publication_date AND i.status='complete') integrated
     FROM legal.source_periods p ORDER BY p.source_id,p.publication_date''').fetchall()
    issues=[]
    required=source_scope.get('required_source_ids') or [r[0] for r in sources]
    source_map={r[0]:r for r in sources}
    reviewed=reviewed_all_publication_sources(source_scope,source_scope.get('_audit_root',Path(__file__).resolve().parents[3]/'sources'))
    for key in required:
        row=source_map.get(key)
        if not row:issues.append({'source_id':key,'code':'SOURCE_MISSING'});continue
        if row[1]!='boe_bulletin' and key not in reviewed:issues.append({'source_id':key,'code':'ALL_PUBLICATION_ADAPTER_OR_AUDIT_PENDING'})
        if row[2]!='verified':issues.append({'source_id':key,'code':'SOURCE_TERMS_AND_COMPLETENESS_UNVERIFIED'})
        if row[3] is None or not now-timedelta(hours=36)<=row[3]<=now+timedelta(minutes=5):issues.append({'source_id':key,'code':'SYNC_STALE_OR_MISSING'})
    expected=sum(r[2] or 0 for r in periods) if periods and all(r[2] is not None for r in periods) else None
    integrated=sum(r[5] for r in periods)
    index_pending=number('SELECT count(*) FROM legal.bulletin_chunks WHERE embedding IS NULL')
    baseline_index_pending=number('SELECT count(*) FROM legal.chunks WHERE embedding IS NULL')
    errors=[];checked=0
    root=Path(storage_root).resolve() if storage_root else None
    if verify_files:
        if root is None:raise ValueError('Storage root required')
        for row in conn.execute('SELECT id,object_key,sha256 FROM legal.publication_assets UNION ALL SELECT id,object_key,sha256 FROM legal.publications'):
            path=(root/row[1]).resolve();checked+=1
            if not path.is_relative_to(root) or not path.is_file():errors.append({'asset_id':row[0],'code':'ORIGINAL_MISSING'});continue
            with path.open('rb') as file:digest=hashlib.file_digest(file,'sha256').hexdigest()
            if digest!=row[2]:errors.append({'asset_id':row[0],'code':'ORIGINAL_HASH_MISMATCH'})
    missing_assets=number("SELECT count(*) FROM legal.bulletin_items i WHERE i.status='complete' AND NOT EXISTS(SELECT 1 FROM legal.publication_assets a WHERE a.source_id=i.source_id AND a.external_id=i.external_id AND a.mime_type='application/pdf')")
    last=min((source_map[k][3] for k in required if k in source_map and source_map[k][3] is not None),default=None)
    # Every geographic entity needs a current/history coverage row backed by the matching
    # expanded-scope source audit. Review hashes cannot be substituted by local counts.
    covered=conn.execute("SELECT jurisdiction_id,source_id,audit_sha256,reviewer,current_to,history_from,history_to FROM legal.coverage WHERE status='verified'").fetchall()
    current_entities={r[0] for r in covered if r[1] in reviewed and r[2]==source_scope.get('audits',{}).get(r[1],{}).get('sha256') and r[3] and r[4] and r[4]>=now.date() and r[5] and r[6]}
    entities=conn.execute('SELECT id,verified FROM legal.jurisdictions').fetchall()
    national_verified=bool(entities) and all(r[1] and r[0] in current_entities for r in entities) and set(required)<=reviewed and not issues
    dimensions=completion_dimensions(expected=expected,integrated=integrated,assets_missing=missing_assets+len(errors),index_pending=index_pending+baseline_index_pending,national_verified=national_verified,last_success=last,now=now)
    if issues:dimensions['freshness']='stale';dimensions['all_complete']=False
    return {'generated_at':now.isoformat(),**dimensions,'scope':'all_publicly_accessible_official_bulletin_items',
      'required_jurisdictions':number('SELECT count(*) FROM legal.jurisdictions'),'required_sources':len(required),
      'captured_catalogue_expected_items':expected,'integrated_items':integrated,
      'bulletin_items':number('SELECT count(*) FROM legal.bulletin_items'),'bulletin_index_pending':index_pending,
      'consolidated_index_pending':baseline_index_pending,'missing_original_assets':missing_assets,
      'files_verified':checked,'file_errors':errors,'file_integrity_status':'checked' if verify_files else 'not_run',
      'periods':[{'source_id':r[0],'date':r[1].isoformat(),'expected':r[2],'status':r[3],'integrated':r[5]} for r in periods],
      'blockers':issues+([] if national_verified else [{'code':'NATIONAL_ALL_PUBLICATION_CURRENT_HISTORY_AUDITS_PENDING'},{'code':'ANNEX_AND_SUBITEM_INVENTORY_UNVERIFIED'}]),
      'limitations':['Finite captured catalogue counts do not prove nationwide completeness or historical availability.','404 is not proof that no bulletin was expected.','Normative-only approvals cannot approve the expanded bulletin scope.']}
