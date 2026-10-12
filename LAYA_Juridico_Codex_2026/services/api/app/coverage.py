from .contracts import CoverageReport
from .config import ROOT
import json


class CoverageService:
    def __init__(self,db):self.db=db

    async def report(self,context):
        async with self.db.tenant_transaction(context) as conn:
            counts=await (await conn.execute("""SELECT
              (SELECT count(*) FROM legal.jurisdictions) total_jurisdictions,
              (SELECT count(*) FROM legal.instruments) legal_instruments,
              (SELECT count(*) FROM legal.section_versions) section_versions,
              (SELECT count(*) FROM legal.chunks) total_chunks,
              (SELECT count(*) FROM legal.chunks WHERE embedding IS NOT NULL) embedded_chunks""")).fetchone()
            sources=await (await conn.execute("SELECT id,name,official_url,audit_status,last_checked_at,last_successful_sync,limitations FROM legal.sources ORDER BY id")).fetchall()
            revision=await (await conn.execute("SELECT inventory_revision FROM legal.jurisdictions WHERE id='ES'")).fetchone()
        # A DB row/directory mapping is not an independently reviewed national coverage audit.
        processing={}
        path=ROOT/"verification/reports/document-processing.json"
        if path.is_file():
            try:processing=json.loads(path.read_text(encoding="utf-8"))
            except (ValueError,OSError):pass
        return CoverageReport(**counts,document_processing=processing,required_inventory_revision=revision["inventory_revision"] if revision else None,
             missing_jurisdictions=counts["total_jurisdictions"],sources=sources,
             gaps=["NATIONAL_SOURCE_AUDIT_PENDING","CURRENT_AND_AVAILABLE_HISTORY_RECONCILIATION_PENDING"],
             limitations=["Inventario geográfico importado; cobertura normativa nacional aún no verificada.",
                          "Los textos consolidados son informativos. Las fechas de vigencia requieren revisión de evidencia."])
