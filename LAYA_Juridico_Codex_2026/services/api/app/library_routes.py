from uuid import UUID
from fastapi import APIRouter,Depends,Request,Query,Response
from .auth import require_context
from .contracts import Contract,TenantContext
from .library import LibraryService
from pydantic import Field

router=APIRouter(prefix='/v1')
class Named(Contract):
    name:str=Field(min_length=1,max_length=200)
    parent_id:UUID|None=None
class DocumentEdit(Contract):
    filename:str|None=Field(default=None,min_length=1,max_length=200)
    folder_id:UUID|None=None
    move:bool=False
class Note(Contract):
    notebook_id:UUID|None=None
    document_id:UUID|None=None
    page_number:int|None=Field(default=None,ge=1)
    start_offset:int|None=Field(default=None,ge=0)
    end_offset:int|None=Field(default=None,gt=0)
    body:str=Field(max_length=50000)
    revision:int|None=Field(default=None,ge=1)
class Reference(Contract):
    section_version_id:str=Field(max_length=200)
def service(request):return LibraryService(request.app.state.db,request.app.state.settings)

@router.get('/documents')
async def documents(request:Request,folder_id:UUID|None=None,query:str=Query('',max_length=200),trash:bool=False,cursor:UUID|None=None,limit:int=Query(50,ge=1,le=100),context:TenantContext=Depends(require_context)):
    return await service(request).list_documents(context,folder_id=folder_id,query=query,trash=trash,cursor=cursor,limit=limit)
@router.get('/folders')
async def folders(request:Request,context:TenantContext=Depends(require_context)):return await service(request).folders(context)
@router.post('/folders')
async def folder(body:Named,request:Request,context:TenantContext=Depends(require_context)):return await service(request).create_folder(context,body.name,body.parent_id)
@router.post('/folders/{key}/move')
async def move_folder(key:UUID,body:Named,request:Request,context:TenantContext=Depends(require_context)):
    await service(request).move_folder(context,key,body.parent_id);return {'id':key}
@router.get('/notebooks')
async def notebooks(request:Request,context:TenantContext=Depends(require_context)):return await service(request).notebooks(context)
@router.post('/notebooks')
async def notebook(body:Named,request:Request,context:TenantContext=Depends(require_context)):return await service(request).create_notebook(context,body.name,body.parent_id)
@router.get('/notebooks/{key}')
async def get_notebook(key:UUID,request:Request,trash:bool=False,context:TenantContext=Depends(require_context)):return await service(request).get_notebook(context,key,trash=trash)
@router.post('/notes')
async def note(body:Note,request:Request,context:TenantContext=Depends(require_context)):
    if not body.notebook_id:
        from .errors import DomainError
        raise DomainError('NOTEBOOK_REQUIRED',422)
    return await service(request).save_note(context,body.model_dump())
@router.post('/notes/{key}')
async def edit_note(key:UUID,body:Note,request:Request,context:TenantContext=Depends(require_context)):return await service(request).save_note(context,body.model_dump(),key)
@router.post('/notebooks/{key}/references')
async def reference(key:UUID,body:Reference,request:Request,context:TenantContext=Depends(require_context)):return await service(request).save_reference(context,key,body.section_version_id)
@router.post('/documents/{key}/metadata')
async def document_edit(key:UUID,body:DocumentEdit,request:Request,context:TenantContext=Depends(require_context)):return await service(request).update_document(context,key,**body.model_dump())
@router.post('/documents/{key}/trash')
async def trash(key:UUID,request:Request,context:TenantContext=Depends(require_context)):return await service(request).update_document(context,key,trash=True)
@router.post('/documents/{key}/restore')
async def restore(key:UUID,request:Request,context:TenantContext=Depends(require_context)):return await service(request).update_document(context,key,trash=False)
@router.get('/documents/{key}/trash-notes')
async def trash_notes(key:UUID,request:Request,context:TenantContext=Depends(require_context)):return await service(request).trash_notes(context,key)
@router.post('/trash/empty')
async def empty_trash(request:Request,context:TenantContext=Depends(require_context)):
    from .library import writable
    writable(context)
    rows=await service(request).list_documents(context,trash=True,limit=100)
    for row in rows['items']:await request.app.state.documents.delete(context,row['id'],trash_only=True)
    return {'deleted':len(rows['items']),'has_more':bool(rows['next_cursor'])}
