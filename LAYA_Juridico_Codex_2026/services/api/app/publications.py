"""Read stored exact versions and integrity-checked official assets; never proxy URLs."""
import asyncio,hashlib
from fastapi import APIRouter,Depends,Request
from fastapi.responses import StreamingResponse
from .auth import require_context
from .contracts import TenantContext
from .errors import DomainError

router=APIRouter(prefix='/v1')
@router.get('/section-versions/{key}')
async def version(key:str,request:Request,context:TenantContext=Depends(require_context)):
    async with request.app.state.db.tenant_transaction(context) as conn:
        if key.startswith('bulletin:'):
            item=await (await conn.execute('SELECT * FROM legal.bulletin_items WHERE id=%s AND status=%s',(key.removeprefix('bulletin:'),'complete'))).fetchone()
            if not item:raise DomainError('VERSION_NOT_FOUND',404)
            assets=await (await conn.execute("SELECT id,official_url,mime_type,sha256,kind FROM legal.publication_assets WHERE source_id=%s AND external_id=%s AND kind='original_publication'",(item['source_id'],item['external_id']))).fetchall()
            return {**item,'id':key,'heading':item['category'],'publication_url':item['official_url'],'is_consolidated':False,'consolidation_date':None,'effectiveness_verified':False,'assets':assets,'original_status':'available' if assets else 'not_captured'}
        row=await (await conn.execute('''SELECT v.*,s.heading,s.instrument_id,i.title,i.official_reference,p.is_consolidated,p.official_url publication_url
          FROM legal.section_versions v JOIN legal.sections s ON s.id=v.section_id JOIN legal.instruments i ON i.id=s.instrument_id
          JOIN legal.publications p ON p.id=v.publication_id WHERE v.id=%s''',(key,))).fetchone()
        if not row:raise DomainError('VERSION_NOT_FOUND',404)
        original_id=row['version_ref'].split(':')[0]
        assets=await (await conn.execute("SELECT id,official_url,mime_type,sha256,kind FROM legal.publication_assets WHERE external_id=%s AND kind='original_publication' ORDER BY created_at DESC LIMIT 20",(original_id,))).fetchall()
    return {**row,'assets':assets,'original_status':'available' if assets else 'not_captured','warnings':['CONSOLIDATED_INFORMATIONAL'] if row['is_consolidated'] else []}

@router.get('/publication-assets/{key}/download')
async def asset(key:str,request:Request,context:TenantContext=Depends(require_context)):
    async with request.app.state.db.tenant_transaction(context) as conn:
        row=await (await conn.execute('SELECT * FROM legal.publication_assets WHERE id=%s',(key,))).fetchone()
        if not row:raise DomainError('ASSET_NOT_FOUND',404)
    root=request.app.state.settings.public_storage_path.resolve();path=(root/row['object_key']).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise DomainError('ASSET_UNAVAILABLE',503)
    def verified():
        # Hold the same file descriptor across verification and streaming.
        with path.open('rb') as file:
            digest=hashlib.file_digest(file,'sha256').hexdigest()
            if digest!=row['sha256']:raise DomainError('ASSET_INTEGRITY_FAILED',503)
            file.seek(0)
            return file.read()
    data=await asyncio.to_thread(verified)
    return StreamingResponse(iter([data]),media_type=row['mime_type'],headers={'Content-Disposition':'inline'})
