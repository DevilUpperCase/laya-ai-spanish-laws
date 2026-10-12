"""Durable, leased extraction and purge worker. Jobs contain IDs/status only."""
import asyncio
import json
import os
from pathlib import Path
import sys
import subprocess
from uuid import UUID
from .contracts import TenantContext
from .documents import DocumentService
from .errors import DomainError


class JobWorker:
    def __init__(self,db,settings):
        self.db,self.settings=db,settings
        self.documents=DocumentService(db,settings)
        from .embeddings import EmbeddingClient
        self.embeddings=EmbeddingClient(settings)

    async def run_once(self,document_id=None):
        async with self.db.pool.connection() as conn:
            await conn.execute('SELECT private.recover_exhausted_jobs()')
            job=await (await conn.execute("SELECT * FROM private.lease_document_job(%s)",(document_id,))).fetchone() if document_id else await (await conn.execute("SELECT * FROM private.lease_job()")).fetchone()
        if not job:return False
        context=TenantContext(user_id=UUID(int=0),tenant_id=job["tenant_id"],role="admin")
        try:
            async with self.db.tenant_transaction(context) as conn:
                row=await (await conn.execute("SELECT * FROM private.documents WHERE id=%s",(job["document_id"],))).fetchone()
                if not row or (job["kind"] in {"extract","index"} and (row["deleted_at"] or row["deletion_epoch"]!=job["deletion_epoch"])):
                    await self._finish(conn,job,"cancelled")
                    return True
                if job["kind"]=="purge":
                    if not row["deleted_at"]:
                        raise DomainError("PURGE_WITHOUT_TOMBSTONE",409)
                    await self._purge(conn,job,row)
                    return True
            if job["kind"]=="index":
                from .private_index import index_batch
                await index_batch(self,context,job)
                return True
            path=self.documents.object_path(row["object_key"])
            # Separate process and hard deadline contain untrusted parsers; stdout is private pipe only.
            env=os.environ.copy()
            env["PYTHONPATH"]=str(Path(__file__).resolve().parents[3])
            env["TESSDATA_PREFIX"]=str(self.settings.ocr_data_path)
            command=[sys.executable,"-m","services.api.app.extract_worker",str(path),row["mime_type"],
                    str(self.settings.upload_max_pages),str(self.settings.document_max_chars),"1" if self.settings.ocr_enabled else "0",self.settings.ocr_language]
            process=await asyncio.to_thread(subprocess.run,command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                    creationflags=0x08000000 if os.name=="nt" else 0,env=env,timeout=120)
            output=process.stdout
            if process.returncode:
                code=json.loads(output).get("error","EXTRACTION_FAILED") if output else "EXTRACTION_FAILED"
                raise DomainError(code,409)
            pages=json.loads(output)
            async with self.db.tenant_transaction(context) as conn:
                document=await (await conn.execute("SELECT * FROM private.documents WHERE id=%s FOR UPDATE",(job["document_id"],))).fetchone()
                lease=await (await conn.execute("SELECT lease_token,status FROM private.jobs WHERE id=%s FOR UPDATE",(job["id"],))).fetchone()
                if document["deleted_at"] or document["deletion_epoch"]!=job["deletion_epoch"] or lease["lease_token"]!=job["lease_token"] or lease["status"]!="processing":
                    return True
                await conn.execute("DELETE FROM private.chunks WHERE document_id=%s",(job["document_id"],))
                for page in pages:
                    await conn.execute("INSERT INTO private.chunks(document_id,tenant_id,page_number,text,ocr_uncertain) VALUES(%s,%s,%s,%s,%s)",(job["document_id"],job["tenant_id"],page["page_number"],page["text"],page["ocr_uncertain"]))
                await conn.execute("UPDATE private.documents SET parse_status='ready',failure_code=NULL WHERE id=%s",(job["document_id"],))
                await conn.execute("INSERT INTO private.jobs(document_id,tenant_id,kind,deletion_epoch) VALUES(%s,%s,'index',%s) ON CONFLICT DO NOTHING",(document["id"],document["tenant_id"],document["deletion_epoch"]))
                await self._finish(conn,job,"complete")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            code=error.code if isinstance(error,DomainError) else "PROCESSING_FAILED"
            async with self.db.tenant_transaction(context) as conn:
                terminal=job["kind"] in {"extract","index"} and (isinstance(error,DomainError) or job["attempts"]>=5)
                await conn.execute("UPDATE private.jobs SET status=%s,failure_code=%s,next_attempt=now()+make_interval(secs=>%s),lease_until=NULL WHERE id=%s AND lease_token=%s",
                                   ("failed" if terminal else "retry",code,min(3600,30*2**min(job["attempts"],7)),job["id"],job["lease_token"]))
                if terminal and job["kind"]=="extract":
                    await conn.execute("UPDATE private.documents SET parse_status='failed',failure_code=%s WHERE id=%s AND deleted_at IS NULL",(code,job["document_id"]))
        return True

    @staticmethod
    async def _finish(conn,job,status):
        await conn.execute("UPDATE private.jobs SET status=%s,lease_until=NULL,lease_token=NULL WHERE id=%s AND lease_token=%s",(status,job["id"],job["lease_token"]))

    async def _purge(self,conn,job,row):
        path=self.documents.object_path(row["object_key"])
        await asyncio.to_thread(path.unlink,missing_ok=True)
        await conn.execute("DELETE FROM private.chunks WHERE document_id=%s",(row["id"],))
        await conn.execute("DELETE FROM private.passage_index WHERE document_id=%s",(row["id"],))
        await conn.execute("DELETE FROM private.notes WHERE document_id=%s",(row["id"],))
        await conn.execute("DELETE FROM private.saved_references WHERE document_id=%s",(row["id"],))
        await conn.execute("UPDATE private.documents SET purged_at=now(),filename='deleted',sha256='',failure_code=NULL WHERE id=%s AND deleted_at IS NOT NULL",(row["id"],))
        await conn.execute("UPDATE private.deletion_records SET purged_at=now() WHERE document_id=%s",(row["id"],))
        await self._finish(conn,job,"complete")


async def main():
    from .config import Settings
    from .database import Database
    settings=Settings()
    db=Database(settings.worker_database_url,worker=True)
    await db.open()
    worker=JobWorker(db,settings)
    try:
        while True:
            if not await worker.run_once():await asyncio.sleep(2)
    finally:
        await db.close()


if __name__=="__main__":
    if os.name=="nt":asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
