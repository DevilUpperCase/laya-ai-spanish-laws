# Planned API contract

Version: v1. Machine-readable endpoint inventory: api-contract.json. It is **not OpenAPI**, a server, or an assertion that endpoints exist. S4 exports real FastAPI OpenAPI.

All business endpoints require verified local auth and an authorized active-tenant context. Public legislation is tenant-neutral; private selections/documents remain scoped. Tenant selection can be supplied as a header but must be validated against membership. Never trust it alone. Health only exposes liveness; readiness is authenticated/internal and reveals no secrets.

| Method/path | Input | Output / behavior |
|---|---|---|
| GET /health | None | 200 liveness without internals. |
| GET /ready | Internal bearer | 200 verified dependency readiness; 503 otherwise. |
| POST /v1/search | SearchRequest | SearchResponse; public results and tenant-authorized selection context. |
| POST /v1/documents | PDF/DOCX multipart, idempotency key | 202 DocumentRecord queued; 413 oversize, 415 unsupported; quarantine/validation before extraction. |
| GET /v1/documents/{document_id} | UUID | DocumentRecord with authorized page/chunk references. |
| GET /v1/documents/{document_id}/download | UUID | Authorized revocable download gateway; not an unrevocable public link. |
| DELETE /v1/documents/{document_id} | UUID | 204 after immediate tombstone/access denial; purge completes asynchronously. Repeated authorized deletion is idempotent. |
| POST /v1/documents/{document_id}/search-related | DocumentSelection + optional query | SearchResponse using saved authorized spans. |
| GET /v1/instruments/{instrument_id}/versions | canonical ID, optional as_of | Versions/relationships/provenance and unknown-validity warnings. |
| GET /v1/coverage | Optional territory IDs | CoverageReport with verified ranges, missing entities/periods and sync state. |

## Types and validation

- **TenantContext:** user_id UUID, tenant_id UUID, role admin/lawyer/reader; produced by trusted code, never deserialized from a request body.
- **SearchRequest:** query string (1..3000 characters in question mode; optional alongside a nonempty document selection), mode question/document, territory_codes list of approved IDs, as_of ISO date or null, legal_types list, include_historical bool, verified_only bool, document_id UUID or null, selection DocumentSelection or null. Document mode requires document_id+selection; question mode rejects private selection fields. Extra fields rejected. Limit query before model token budgeting; do not silently truncate the user's query.
- **DocumentSelection:** page_number >=1, start_offset >=0, end_offset > start_offset, optional selected_text for consistency checking only. Offsets are Unicode character offsets in the stored page text, not bytes or browser UTF-16 offsets; UI translates accordingly. DOCX uses logical rendered sections/pages without inventing original PDF bboxes.
- **RetrievalQuery:** resolved query, approved territory/date/type filters, TenantContext and trace_id; no full document attached.
- **Candidate:** candidate_id, instrument_id, section_version_id, heading, passage, language_code, jurisdiction_code, official_reference, official_url, publication_date, effective_from/to, effectiveness_verified, validity_status, source_id and original offsets. Candidate IDs are stable and unique.
- **Decision:** candidate_id, label none/partial/direct, probabilities mapping label->finite float [0,1], answer_confidence finite float [0,1] or null, abstained bool or unknown, truncated bool or unknown, model_revision and latency. Require compatible full metadata before rank influence; no legal probability claim.
- **Reason:** kind, message, evidence object with source/version IDs and original query/article span or verified metadata; all asserted factual values are traceable. Unknown validity produces a warning, not an inferred effective date.
- **SearchResponse:** results list, coverage CoverageReport, warnings list of stable codes with localized display, trace_id, engines {retrieval, laya_mode, laya_status}. Each result contains candidate fields, literal snippet, verified citations, reason list and ranking signals. No generic generated answer field.
- **DocumentRecord:** id, tenant_id (authorized response only), parse_status queued/processing/ready/failed/deleted, mime_type, pages/selection availability, OCR uncertainty and redacted failure code. No private raw storage path in browser response.
- **ProcessingJob:** job_id, document_id, tenant_id, kind, lease_until, attempts, idempotency_key, status, deletion_epoch; no raw text in persisted workflow/job metadata.
- **CoverageReport:** required_inventory_revision, status blocked/verified, entity/source mappings, audited ranges, last_checked_at, last_integrated_publication, last_successful_sync, gaps and limitations. A recent source check does not mean successful ingestion.

## Errors and cancellation

401 invalid/missing authentication; 403 unauthorized active tenant/role; 404 unknown or inaccessible document (same response to avoid existence disclosure); 409 selection/processing-state conflict; 422 invalid fields/offsets; 429 API limits; 503 unavailable essential storage/DB/readiness. LAYA-only failure normally returns 200 with baseline and LAYA_DEGRADED warning. Corpus empty returns an empty result list plus coverage warnings. No private exception bodies.

Recheck document authorization/deletion before returning selection-linked responses. Tombstoned document access is denied even when a job/search was already running. Deletion does not cancel a legitimate independent public-law query, but private selection content cannot be returned after its authorization has changed.
