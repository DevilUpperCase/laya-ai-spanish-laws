import hmac
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, UploadFile, File, Header, Response
from uuid import UUID
from urllib.parse import quote
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .auth import Authenticator, require_context
from .config import Settings
from .contracts import SearchRequest, TenantContext, SearchResponse, DocumentRecord, DocumentSelection, CoverageReport
from .database import Database
from .errors import DomainError
from .documents import DocumentService
from .selection import SelectionService
from .coverage import CoverageService
from .retrieval import HybridRetriever
from .embeddings import EmbeddingClient
from .laya_client import LayaClient
from .search import SearchService
from .body_limit import BodyLimitMiddleware
from .browser_auth import router as auth_router, csrf_allowed
from collections import defaultdict, deque
from .library_routes import router as library_router
from .publications import router as publication_router


def create_app(settings: Settings | None = None, *, connect: bool = True) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.db = Database(settings.database_url) if connect and settings.database_url else None
        if app.state.db:
            await app.state.db.open()
            app.state.embeddings=EmbeddingClient(settings)
            app.state.laya=LayaClient(settings)
            app.state.documents=DocumentService(app.state.db,settings)
            app.state.selection=SelectionService(app.state.db)
            app.state.coverage=CoverageService(app.state.db)
            retriever=HybridRetriever(app.state.db,app.state.embeddings)
            app.state.search=SearchService(retriever,app.state.laya,app.state.selection,app.state.coverage)
        yield
        if app.state.db:
            await app.state.laya.close()
            await app.state.db.close()

    app = FastAPI(title="LAYA Juridico", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.auth = Authenticator(settings)
    app.state.db = None
    app.state.login_attempts=defaultdict(deque)
    app.include_router(auth_router)
    app.include_router(library_router)
    app.include_router(publication_router)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST", "DELETE"],
                       allow_headers=["Authorization", "X-Tenant-ID", "Idempotency-Key", "Content-Type", "X-Requested-With"],allow_credentials=True)
    app.add_middleware(BodyLimitMiddleware,upload_max_bytes=settings.upload_max_bytes)

    @app.middleware("http")
    async def safe_headers(request: Request, call_next):
        request.state.trace_id = str(uuid.uuid4())
        unsafe=request.method not in {'GET','HEAD','OPTIONS'}
        cookie_request=bool(request.cookies.get('laya_session')) and not request.headers.get('Authorization')
        if unsafe and (cookie_request or request.url.path.startswith('/auth/')) and not csrf_allowed(request):
            return JSONResponse({'error':'CSRF_REJECTED','trace_id':request.state.trace_id},status_code=403,headers={'Cache-Control':'no-store'})
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.trace_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, error):
        return JSONResponse({"error": error.code, "trace_id": request.state.trace_id}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # FastAPI's default includes rejected input, which can contain private text.
        return JSONResponse({"error": "REQUEST_INVALID", "trace_id": request.state.trace_id}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request, error):
        return JSONResponse({"error": "SERVICE_UNAVAILABLE", "trace_id": request.state.trace_id}, status_code=503)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(request: Request):
        supplied = request.headers.get("Authorization", "")
        if not settings.internal_api_key or not hmac.compare_digest(supplied, "Bearer " + settings.internal_api_key):
            raise DomainError("AUTH_REQUIRED", 401)
        dependencies={"database":app.state.db is not None,"laya":False,"embeddings":False,"corpus":False}
        if app.state.db:
            try:
                async with app.state.db.pool.connection() as conn:
                    row=await (await conn.execute("SELECT count(*) n FROM legal.chunks")).fetchone()
                    dependencies["corpus"]=row["n"]>0
                await app.state.embeddings.load()
                dependencies["embeddings"]=bool(settings.embedding_model_revision)
                response=await app.state.laya.client.get("/health")
                health=response.json()
                dependencies["laya"]=health.get("revisions",{}).get("juridico")==settings.laya_model_revision and bool(settings.laya_model_revision)
            except Exception:
                pass
        # Runtime dependencies cannot certify first-release jurisdiction coverage.
        return JSONResponse({"status":"blocked","runtime_ready":all(dependencies.values()),"release_ready":False,
              "dependencies":dependencies,"blockers":["NATIONAL_AUDIT_PENDING","PROFESSIONAL_EVALUATION_PENDING","OPERATIONS_REHEARSAL_PENDING"]},status_code=503)

    @app.post("/v1/search",response_model=SearchResponse)
    async def search(body: SearchRequest, request: Request, context: TenantContext = Depends(require_context)):
        return await app.state.search.search(body,context,request.state.trace_id)

    @app.post("/v1/documents",response_model=DocumentRecord,status_code=202)
    async def upload(file: UploadFile = File(), idempotency_key: str = Header(alias="Idempotency-Key",min_length=1,max_length=128),context: TenantContext = Depends(require_context)):
        return await app.state.documents.upload(context,file,idempotency_key)

    @app.get("/v1/documents/{document_id}",response_model=DocumentRecord)
    async def get_document(document_id: UUID,trash: bool=False,context: TenantContext = Depends(require_context)):
        return await app.state.documents.get(context,document_id,trash=trash)

    @app.get("/v1/documents/{document_id}/download")
    async def download_document(document_id: UUID,trash: bool=False,context: TenantContext = Depends(require_context)):
        row=await app.state.documents.download(context,document_id,trash=trash)
        return StreamingResponse(app.state.documents.stream(context,document_id,row["object_key"],trash=trash),media_type=row["mime_type"],
           headers={"Content-Disposition":"attachment; filename*=UTF-8''"+quote(row["filename"])})

    @app.get("/v1/documents/{document_id}/preview")
    async def preview_document(document_id:UUID,trash:bool=False,context:TenantContext=Depends(require_context)):
        row=await app.state.documents.download(context,document_id,trash=trash)
        if row['mime_type']!='application/pdf':raise DomainError('PREVIEW_UNAVAILABLE',415)
        return StreamingResponse(app.state.documents.stream(context,document_id,row['object_key'],trash=trash),media_type='application/pdf',headers={'Content-Disposition':'inline'})

    @app.delete("/v1/documents/{document_id}",status_code=204)
    async def delete_document(document_id: UUID,context: TenantContext = Depends(require_context)):
        await app.state.documents.delete(context,document_id)
        return Response(status_code=204)

    @app.post("/v1/documents/{document_id}/search-related",response_model=SearchResponse)
    async def related(document_id: UUID,selection: DocumentSelection,request: Request,context: TenantContext = Depends(require_context)):
        body=SearchRequest(mode="document",document_id=document_id,selection=selection)
        return await app.state.search.search(body,context,request.state.trace_id)

    @app.get("/v1/instruments/{instrument_id}/versions")
    async def versions(instrument_id: str,as_of: str | None = None,context: TenantContext = Depends(require_context)):
        from datetime import date
        try:cutoff=date.fromisoformat(as_of) if as_of else date.today()
        except ValueError:raise DomainError("DATE_INVALID",422) from None
        async with app.state.db.tenant_transaction(context) as conn:
            instrument=await (await conn.execute("SELECT * FROM legal.instruments WHERE id=%s",(instrument_id,))).fetchone()
            if instrument is None:raise DomainError("INSTRUMENT_NOT_FOUND",404)
            rows=await (await conn.execute("""SELECT v.id,v.version_ref,v.publication_date,v.consolidation_date,v.effective_from,v.effective_to,v.effectiveness_verified,s.section_key,s.heading,p.official_url,p.sha256
              FROM legal.section_versions v JOIN legal.sections s ON s.id=v.section_id JOIN legal.publications p ON p.id=v.publication_id
              WHERE s.instrument_id=%s AND v.publication_date<=%s ORDER BY s.ordinal,v.publication_date,v.id""",(instrument_id,cutoff))).fetchall()
            relationships=await (await conn.execute("SELECT to_external_id,kind,official_evidence_url,verified FROM legal.relationships WHERE from_instrument=%s",(instrument_id,))).fetchall()
        return {"instrument":instrument,"versions":rows,"relationships":relationships,"warnings":["CONSOLIDATED_INFORMATIONAL","UNKNOWN_EFFECTIVENESS"]}

    @app.get("/v1/coverage",response_model=CoverageReport)
    async def coverage(context: TenantContext = Depends(require_context)):
        return await app.state.coverage.report(context)

    @app.get("/v1/jurisdictions")
    async def jurisdictions(context: TenantContext = Depends(require_context)):
        async with app.state.db.tenant_transaction(context) as conn:
            return await (await conn.execute("SELECT id,name,level,parent_id FROM legal.jurisdictions ORDER BY level,name")).fetchall()

    return app


app = create_app()
