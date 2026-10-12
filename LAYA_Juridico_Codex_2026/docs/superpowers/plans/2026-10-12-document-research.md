# Document Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build original-document readers, explainable intent and attachment search, a shared document notebook with trash, and honest daily official-publication checks.

**Architecture:** Extend the existing tenant-isolated FastAPI/PostgreSQL app with explicit library and bulletin entities. Preserve non-generative local retrieval and mandatory LAYA shadow classification, carry real retrieval evidence into explanations, and coordinate bounded attachment retrieval through LangGraph. Monitor publisher reconciliation independently of processing and vector progress.

**Tech Stack:** Existing locked Python/FastAPI/LangChain Core/LangGraph/LAYA/BGE-M3, PostgreSQL/pgvector and Next.js/TypeScript stack; no generative LLM.

**Spec:** `docs/specs/2026-10-12-document-research.md`

## Global Constraints

- No generative LLMs, external inference/tracing, private query logs or persisted private search graph state.
- Real FastAPI, LangChain Core, LangGraph and local LAYA remain mandatory; LAYA stays in shadow with warned outage fallback.
- Preserve tenant isolation in API, RLS, storage, workers and browser state; no elevated user-search database role.
- Spanish UI; English code/documentation; es/ca/gl/eu search evaluation.
- Recoverable trash has no automatic expiry; permanent deletion revokes access immediately, purges live derivatives within 24 hours and expires encrypted backups within 30 days.
- Nationwide complete means all required jurisdictions/publishers and current plus officially available history, including individual official-bulletin items. Unknown coverage blocks completion.
- Do not alter previously applied migrations. The workspace has no Git repository: record verification checkpoints in the implementation ledger instead of commits.

## Review Focus

- Cross-tenant IDs and logout/workspace changes must revoke preview, attachment and note access; exercise in Tasks 1–4.
- Trash/permanent deletion racing extraction, indexing, search or restore must not leak or resurrect derivatives; exercise in Tasks 1–3.
- A promulgated PDF may differ from the consolidated/historical result text; reader must show that distinction; exercise in Task 2.
- Long natural-language questions or misleading attachments must not erase exact identifiers, explicit filters or semantic evidence; exercise in Task 3.
- Missing catalogue pages, legitimate no-issue days and stale successful runs must never become a nationwide-complete report; exercise in Task 5.

---

## Task 1: Library, notebooks and recoverable trash backend

**Files:** Create `db/migrations/013_document_library.sql`, `services/api/app/library.py`, `tests/integration/test_library.py`; modify `contracts.py`, `documents.py`, `selection.py`, `jobs.py`, `main.py`, `scripts/reapply_deletions.py`, `scripts/rehearse_restore.py` and `db/rollback.md`.

**Interfaces:** `LibraryService.list_documents(context, *, folder_id=None, query='', trash=False, cursor=None, limit=50)` returns a bounded page. Folder/notebook/note create/update/list routes use tenant context and a revision integer. Document routes add `POST /v1/documents/{id}/trash`, `POST .../restore`; `DELETE .../{id}` remains permanent deletion for API compatibility. `POST /v1/trash/empty` permanently deletes a transactionally selected bounded batch and returns a continuation indicator. Preview/list/selection methods default to active documents and accept explicit authorized trash access only for trash routes.

**Data:** `private.folders`, `private.notebooks`, `private.notes`, `private.saved_references`; document folder linkage, display name and `trashed_at`. Composite tenant keys, FORCE RLS and role-bound write policies on every table. Notes have optional document/page/offset anchors, plain-text body and revision. General notebook notes have no document link. No recursive folder move cycles. Trashing preserves data; existing `deleted_at` always means permanent deletion. Worker purge removes all document-linked notes/copied excerpts/private index entries; restore replay performs the same revocation before access.

- [ ] Write failing `test_library_tenant_roles_and_revision_conflicts`, `test_trash_restore_and_permanent_delete`, `test_folder_cycle_rejected`, and `test_deleted_document_notes_not_restored`. Assert reader write=403, foreign IDs=404, stale revision=409, ordinary listing/search excludes trash, trash preserves original/notes, restore succeeds only before permanent deletion, and post-delete access=404.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/integration/test_library.py -q`; verify failures come from missing interfaces.
- [ ] Implement the migration and bounded service/routes, including atomic note revision updates and permanent-deletion cleanup/replay. Update worker INSERT statements with explicit column lists before schema extension.
- [ ] Apply with `scripts/migrate.py`; run the focused tests against real PostgreSQL plus existing document/isolation/deletion tests. Rehearse synthetic trash → backup → restore → permanent delete → deletion replay.
- [ ] Record observed checks/limits and schema recovery in the ledger; do not claim a full production restore.

## Task 2: Original and exact-version readers

**Files:** Create `db/migrations/014_publication_assets.sql`, `services/api/app/publications.py`, `services/ingest/ingest/boe_originals.py`, `apps/web/src/components/document-preview.tsx`, `apps/web/src/app/instruments/[id]/page.tsx`, `tests/integration/test_publication_reader.py`; modify `main.py`, `config.py`, `documents.py`, web document detail, `api.ts`, `results.tsx` and browser tests.

**Interfaces:** `GET /v1/section-versions/{id}` returns literal full section text, offsets, version metadata and linked publication assets. `GET /v1/publication-assets/{id}/download` streams a verified archived asset. `GET /v1/documents/{id}/preview` streams an authenticated PDF inline; trash preview uses explicit trash authorization. `capture_boe_original(identifier, destination, client)` resolves original URLs from trusted official XML/summary metadata, preserves PDF/XML/hash and returns availability metadata; never constructs an unverified PDF URL. A bounded CLI captures missing official originals for an explicit item/instrument batch.

- [ ] Write failing reader tests asserting exact requested version, offset span equality, no source URL forgery, missing-original notice, byte/hash integrity, hostile XML rejection and foreign-tenant/private deletion=404. Browser test opens an uploaded PDF and releases preview state on workspace change/logout.
- [ ] Run focused tests and confirm missing-route/interface failures.
- [ ] Implement safe publication asset storage/readers and original capture with exact host/redirect/body checks. Use PDF blob previews through the fixed authenticated gateway; keep DOCX extracted text plus download. Label original/consolidated/version/effectiveness separately and navigate to the matching section/selection.
- [ ] Capture a real official original, compare archived SHA with response bytes, run API tests, web typecheck/build and real browser reader checks.
- [ ] Document availability limits and update the ledger; never treat a consolidated XML archive as the original promulgated PDF.

## Task 3: Intent-aware retrieval, attachments and evidence

**Files:** Create `db/migrations/015_private_retrieval.sql`, `services/api/app/query_intent.py`, `services/api/app/attachments.py`, `services/api/app/private_retrieval.py`, `tests/search/test_query_intent.py`, `tests/integration/test_attachment_search.py`, `evaluation/compare_query_plans.py`; modify `contracts.py`, `retrieval.py`, `fusion.py`, `explanations.py`, `search.py`, `search_graph.py`, `jobs.py`, `selection.py`, `config.py`, web `page.tsx`, `api.ts` and `results.tsx`.

**Interfaces:** Extend `SearchRequest` with optional user-supplied `intent` fields (`issue`, `objective`) and up to 10 unique `attachment_ids`, plus `scope` (`normative`/`all_publications`/`attachments`). Existing question/document-selection requests remain valid. `build_query_plan(request) -> QueryPlan` retains literal query, exact identifiers and explicit filters; bounds alternative retrieval inputs to four. `AttachmentService.resolve(context, ids, query_plan) -> AttachmentContext` verifies every requested active ready file and selects at most four source-backed 1,200-character passages. `PrivateRetriever.ainvoke(query) -> list[PrivateResult]` returns document/page/offset citations. `SearchResponse` adds interpreted intent, context evidence and typed private results while retaining legacy public results.

**Data and evidence:** Separate private passage index has literal page/start/end offsets, FTS and pinned 1024-d embeddings; split into 1,000-character passages with 120-character overlap. Durable indexing stores document derivatives, not queries. Preserve a document deletion epoch and recheck every attached/returned document after inference. Persist no per-query context. Candidate retrieval evidence records engine, rank and fusion contribution; scores are retrieval signals, not legal relevance probabilities. LAYA classifier status is explicitly shadow and never fabricated as a result reason.

- [ ] Write failing tests for natural-language query with no literal relevant-word overlap, exact-reference preservation, explicit-date/territory preservation, ancestor/descendant scope, two attachments, foreign/trash/deleted/not-ready IDs, OCR warnings and indexing/search races. Assert every displayed explanation is backed by the engine result or a literal authorized span.
- [ ] Run focused tests; use fixed deterministic embeddings only for unit invariants, never as evidence of real model quality.
- [ ] Implement structured intent and bounded semantic queries, broaden sparse recall without inventing synonym/legal facts, preserve engine ranks through fusion, and add private indexing/retrieval under RLS. Update LangGraph to resolve attachments, retrieve by explicit scope and recheck access. Retain existing local LAYA invocation/fallback for official candidates.
- [ ] Implement optional Spanish refinement fields with 'unknown' support and editable interpretation, direct search, upload/existing-file attachment chips, readiness status, mode controls and per-result source/context explanations. Warn when selected passage budgets truncate context; never append whole files.
- [ ] Run real BGE/LAYA integration checks, isolation tests, web typecheck/build and browser two-file flows. Run calibration comparison tooling on supplied reviewed public cases; mark professional quality/training decisions pending when labels are unavailable. Retain the original holdout unchanged.
- [ ] Record query-quality evidence and limits. Add a training-readiness report requiring reviewed candidate labels/model compatibility/resources/held-out improvement before recommending LAYA adaptation; do not claim trained or 'best' without measurements.

## Task 4: Drive/notebook/trash UI

**Files:** Create `apps/web/src/components/document-library.tsx`, `apps/web/src/components/notebook-editor.tsx`, `apps/web/src/app/notebooks/[id]/page.tsx`, `apps/web/src/app/trash/page.tsx`, `tests/e2e/document-workspace.cjs`; modify documents landing/detail, `workspace.tsx`, `api.ts`, UI styles and shared browser helpers.

**Interfaces:** Consume Task 1 library/note routes and Task 2 reader routes. Library exposes folder navigation, filename search, ready/queued/failed states, upload, rename/move and case-notebook links. Notebook exposes manually saved general/document-anchored notes and references with revision checks. Trash exposes restore and explicitly confirmed permanent delete/empty; ordinary 'Eliminar' becomes 'Mover a Papelera' in UI while preserving the API's existing DELETE semantics.

- [ ] Write browser cases for upload→list→folder→note→reload, selected-page note/reference, stale edit conflict, reader read-only, trash→hidden from attachments→preview in trash→restore, and permanent delete=404. Use synthetic documents only.
- [ ] Implement the UI and authenticated previews, with visible distinction between manual notes and source quotes. Clear unsaved sensitive state on tenant/session change. Labels explain trash retention and irreversible deletion.
- [ ] Run typecheck, production build and real desktop/mobile keyboard/browser flows; inspect captures and error/empty/loading states.
- [ ] Update APP_GUIDE/DEVELOPER_GUIDE and the ledger with actual behavior and browser evidence.

## Task 5: Expanded bulletin corpus and daily completion reports

**Files:** Create `db/migrations/016_bulletin_monitoring.sql`, `services/ingest/ingest/boe_bulletin.py`, `services/ingest/ingest/bulletin_pipeline.py`, `services/ingest/ingest/processing_status.py`, `scripts/sync_bulletins.py`, `scripts/check_document_processing.py`, `scripts/daily_document_check.py`, `tests/ingest/test_boe_bulletin.py`, `tests/ops/test_document_processing.py`, `sources/bulletin-scope.json`; modify public retrieval/routes/contracts, `coverage.py`, supervisor scheduling, verification reports and operator/source docs.

**Interfaces:** Bulletin adapter separates BOE and BORME daily catalogue sources, parses actual summary item/asset IDs and captures original content, category, publisher, date and attachments. `collect_processing_status(conn, source_scope, *, now, verify_files=False) -> ProcessingReport` reports `snapshot_processing`, `national_coverage`, `freshness`, counts and explicit blockers. CLI `check_document_processing.py --verify-files` writes dated JSON/Markdown and exits 0 only when every requested completion dimension passes; blocked=1, operational failure=2. `daily_document_check.py` holds a lifetime lock, runs bounded seven-day reconciliation for supported sources, invokes the checker, preserves failures and writes a next-run/last-success status. It supports Windows supervisor and a documented Linux timer command.

**Data:** Distinct `legal.bulletin_items`, original assets, item text/index and source-period reconciliation. Normative/publication classification records publisher/category evidence; unknown classification appears only in all-publications scope and blocks normative classification acceptance. Do not force administrative notices into normative instruments. Source period expectations come from official catalogue/issue evidence, never from local integrated counts. Represent empty official periods explicitly. Every required publisher is in the monitoring inventory, including unsupported adapters with blocking reasons.

- [ ] Write failing tests using actual summary fixtures for normative/administrative items and attachments, BOE versus BORME namespacing, pagination gaps, missing parse/vector/original, hash mismatch, stale last-success, blocked unknown expected counts, documented no-issue days and unsupported publishers. Assert complete captured snapshot cannot set national completion=true.
- [ ] Capture primary official fixtures and schema evidence; implement bounded original item ingestion for BOE/BORME without guessing historical availability. Preserve source attribution and reuse review status. Add normative/all-publication retrieval and reader links with separate administrative warnings.
- [ ] Implement snapshot/coverage/freshness checks and daily orchestration without shell-string commands. Integrate a once-per-day supervised run after success and bounded failed-run retries. Retain existing consolidated BOE update reconciliation. Define 'daily' as every 24 hours while the machine is running, with catch-up after restart and visible downtime/staleness.
- [ ] Run focused tests and a real bounded date-window import/check. Verify national status remains blocked for missing regional/provincial/municipal/island/foral catalogues/history. Run checker with archived-file verification and retain dated counts/blockers, not a fabricated all-Spain success.
- [ ] Document commands, scheduling and adapter-extension contracts; update coverage/release limitations to the expanded scope. Existing normative-only audits cannot approve all-publication completeness.

## Final verification and handoff

- [ ] Run appropriate focused checks after each task, then the complete integration suite with a controlled private-worker pause/resume, actual model readiness, Next.js typecheck/build and real browser flows. Re-run only checks justified by subsequent changes.
- [ ] Run offline package verification and expected-failing national/release checks; refresh API contracts/code documentation and implementation ledger. Keep real original fixtures and human documentation/diagrams current.
- [ ] Perform one independent read-only completion review as required by executing-plans, address material findings with meaningful regressions, and report implemented behavior separately from pending nationwide audits/professional evaluation/training decisions.

## Plan self-review

All eight confirmed product behaviors map to Tasks 1–5. Five review-focus conditions have explicit owning tests. Permanent DELETE compatibility, non-generative intent, original/version distinction, private index lifecycle and finite-versus-national completeness are defined once and used consistently. The original release gates remain mandatory; the broader bulletin scope raises the evidence requirement instead of weakening it. Implementation follows final owner design confirmation requested by the explicitly invoked grilling skill.
