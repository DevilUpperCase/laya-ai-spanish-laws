# Data, source and security contract

db/001_base.sql is an inspected draft. F2 turns it into reviewed versioned migrations; the offline verifier does not execute SQL or certify RLS.

## Legal corpus

| Entity | Identity / required provenance |
|---|---|
| legal_sources | Stable code, publisher/level, official home, approved terms, audited capability/ranges and successful sync metadata. |
| jurisdictions | Official dated geographic ID, level, parent, names/translations; preserve historical code changes rather than matching OCR names blindly. |
| legal_instruments | Canonical identity/ELI or source ref, official title/type/issuer/jurisdiction; lifecycle facts require evidence. |
| legal_publications | Source + stable official ref/content identity, original URL/format/hash/blob, publication_date and ingestion timestamp. |
| legal_sections | Instrument + stable section key; headings/ordering separate from section text versions. |
| legal_section_versions | Section/publication ref, publication_date, effective_from/to, explicit effectiveness_verified, original text/language/hash/version_ref. |
| legal_relationships | From/to instruments, kind, official evidence publication/URL, verified flag; no inferred tacit repeal. |
| legal_chunks | Version/ordinal, original Unicode offsets, local embedding/model revision, deterministic FTS configuration. |
| ingest_runs | Source/window/cursor/counts/status/timestamps/gaps; status partial/failed cannot advance freshness as complete. |

Unknown effective_from/to remains null and does not mean current/open-ended validity. Add integrity checks for verified effectiveness provenance and ordered date ranges. Deduplicate dual BOE/regional publication via curated canonical equivalence while preserving both original publications/languages.

Draft unique keys contain nullable refs: PostgreSQL nullable uniqueness cannot by itself ensure idempotency. F2 defines deterministic non-null publication/version keys (including source reference when available and original content identity) and unique constraints; different evidenced editions are preserved. Exact external identifiers never come from generated similarity.

## Private entities and invariants

- tenants and tenant_members: reviewed roles and user memberships; service role is never a browser/user-search credential.
- client_documents: UUID, tenant_id, uploader, private object key, MIME/hash, parse status, deletion_epoch, deleted_at, purge_due_at and purged_at. Original filename is private metadata and not logged.
- client_chunks: document_id, tenant_id, ordinal/page/offsets/text/vector. Add a unique document `(id,tenant_id)` parent key and composite chunk foreign key `(document_id,tenant_id)` to that key; independent FKs alone do not prevent parent-tenant mismatch.
- document_jobs: document/tenant linkage, lease, attempts, next retry, idempotency and deletion_epoch. Recheck tombstones on processing and writes.
- deletion_records: document/tenant IDs and deadlines/completion only, retained beyond usable backups/restore window. Restores apply records before reopening access.
- source audits and coverage mappings: source/adapter version, geographic IDs, current/available-history windows, fixture/provenance/terms/reconciliation evidence and independent reviewer. One publisher can cover many entities.

## RLS and storage

User transactions use a non-owner/non-BYPASSRLS role, verified identity and trusted active-tenant context. Membership alone is insufficient for a user belonging to two tenants: policy requires the selected tenant too. Transaction context must reset on pool reuse. Test direct SQL, not only filtered API queries. Grant only required operations; add mutation policies or restricted procedures for approved roles, never broad ALL policies.

Private chunks require a nondeleted authorized parent. Storage policies enforce tenant/document prefixes and tombstones; quarantine/derivative paths are included. Revocable gateway authorization applies to previously issued download access. Public originals are kept separate from client files. Backend workers/corpus ingestion have isolated restricted identities with audited parent checks; a privileged worker is not evidence that RLS protects against its bugs.

## Other draft gaps to close

Explicit extension/schema grants, auth/storage dependencies, HNSW cosine operator alignment, multilingual FTS/normalization, foreign-key indexes, role mutations, durable jobs, tombstones, source reconciliation and provenance-backed effectiveness checks need migrations/tests. Applying the same draft twice can fail on existing policies; migrations have recorded versions, repeatable startup and rollback/recovery procedures.

## Source interfaces

S1 defines PublicationRef (source_id/external_id/official URL/date), RawPublication (original bytes/format/hash/fetch metadata), ParsedPublication (instrument/publications/section versions/relations/language/territory), DiscoveryPage (refs/next cursor/reported totals), ReconciliationReport (expected/discovered/integrated counts, missing intervals and evidence), SourceHealth and IngestRun.

Adapters implement discover/fetch/parse/reconcile/healthcheck. They must preserve official metadata without inventing URLs/effective dates and classify normative acts rather than individual announcements. Capability and terms approval precede bulk ingestion. Every source has fixtures with original URL/fetch timestamp/hash and reviewed ranges.
