from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class TenantContext(Contract):
    user_id: UUID
    tenant_id: UUID
    role: Literal["admin", "lawyer", "reader"]


class DocumentSelection(Contract):
    page_number: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    selected_text: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_offset <= self.start_offset or self.end_offset - self.start_offset > 3000:
            raise ValueError("Selection must contain 1..3000 Unicode characters")
        return self


class QueryIntent(Contract):
    issue: str = Field(default="",max_length=1000)
    objective: str = Field(default="",max_length=1000)


class SearchRequest(Contract):
    intent: QueryIntent | None = None
    attachment_ids: list[UUID] = Field(default_factory=list,max_length=10)
    scope: Literal["normative","all_publications","attachments"] = "normative"
    query: str = Field(default="", max_length=3000)
    mode: Literal["question", "document"] = "question"
    territory_codes: list[str] = Field(default_factory=list, max_length=50)
    as_of: date | None = None
    legal_types: list[str] = Field(default_factory=list, max_length=30)
    include_historical: bool = False
    verified_only: bool = False
    document_id: UUID | None = None
    selection: DocumentSelection | None = None

    @model_validator(mode="after")
    def valid_mode(self):
        if len(self.attachment_ids)!=len(set(self.attachment_ids)):
            raise ValueError("Duplicate attachments")
        if self.scope=="attachments" and not self.attachment_ids:
            raise ValueError("Attachment scope requires documents")
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in self.query):
            raise ValueError("Invalid Unicode")
        if self.mode == "document":
            if self.document_id is None or self.selection is None:
                raise ValueError("Document mode requires a stored selection")
        elif not self.query.strip() or self.document_id is not None or self.selection is not None:
            raise ValueError("Question mode requires a query and excludes document selection")
        return self


class RetrievalQuery(Contract):
    retrieval_inputs: list[str] = Field(default_factory=list)
    retrieval_sources: list[dict] = Field(default_factory=list)
    query: str
    request: SearchRequest
    context: TenantContext
    trace_id: str


class Candidate(Contract):
    retrieval_evidence: list[dict] = Field(default_factory=list)
    candidate_id: str
    instrument_id: str
    section_version_id: str
    heading: str
    passage: str
    language_code: str
    jurisdiction_code: str
    official_reference: str
    official_url: str
    publication_date: date
    effective_from: date | None = None
    effective_to: date | None = None
    effectiveness_verified: bool = False
    validity_status: str = "unknown"
    source_id: str
    start_offset: int
    end_offset: int
    version_ref: str
    consolidation_date: date | None = None
    is_consolidated: bool = True
    ingestion_warnings: list[str] = Field(default_factory=list,exclude=True)
    score: float = 0


class Decision(Contract):
    candidate_id: str
    label: Literal["none", "partial", "direct"]
    probabilities: dict[str, float]
    answer_confidence: float | None = None
    abstained: bool | None = None
    truncated: bool | None = None
    model_revision: str
    latency_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def probability_distribution(self):
        if set(self.probabilities) != {"none", "partial", "direct"}:
            raise ValueError("Missing classification probabilities")
        if any(not 0 <= p <= 1 for p in self.probabilities.values()):
            raise ValueError("Invalid probability")
        if abs(sum(self.probabilities.values()) - 1) > 0.005:
            raise ValueError("Probabilities must sum to one")
        if self.probabilities[self.label] < max(self.probabilities.values()) - 0.0001:
            raise ValueError("Choice is not an argmax")
        if self.answer_confidence is not None and not 0 <= self.answer_confidence <= 1:
            raise ValueError("Invalid answer confidence")
        return self


class Reason(Contract):
    kind: str
    message: str
    evidence: dict[str, str | int | float | bool | None]


class SearchResult(Candidate):
    reasons: list[Reason]
    warnings: list[str]


class CoverageReport(Contract):
    document_processing: dict = Field(default_factory=dict)
    status: Literal["blocked", "verified"] = "blocked"
    required_inventory_revision: str | None = None
    total_jurisdictions: int = 0
    verified_jurisdictions: int = 0
    legal_instruments: int = 0
    section_versions: int = 0
    embedded_chunks: int = 0
    total_chunks: int = 0
    missing_jurisdictions: int = 0
    sources: list[dict] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class SearchResponse(Contract):
    interpreted_query: dict = Field(default_factory=dict)
    context_evidence: list[dict] = Field(default_factory=list)
    private_results: list[dict] = Field(default_factory=list)
    results: list[SearchResult]
    coverage: CoverageReport
    warnings: list[str]
    trace_id: str
    engines: dict[str, str]


class DocumentPage(Contract):
    page_number: int
    text: str
    ocr_uncertain: bool = False


class DocumentRecord(Contract):
    folder_id: UUID | None = None
    trashed_at: datetime | None = None
    id: UUID
    tenant_id: UUID
    filename: str
    parse_status: str
    mime_type: str
    created_at: datetime
    pages: list[DocumentPage] = Field(default_factory=list)
    failure_code: str | None = None


class ProcessingJob(Contract):
    job_id: UUID
    document_id: UUID
    tenant_id: UUID
    kind: str
    attempts: int
    deletion_epoch: int
