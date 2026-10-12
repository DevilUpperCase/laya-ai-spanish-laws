# Remaining issues and feature status

**Project:** LAYA_Juridico_Codex_2026  
**Status checked:** 12 October 2026 (local development)  
**Purpose:** Separate features already present in the code from features that are incomplete, unverified, or blocked. Implemented in code does not mean nationwide coverage, professional legal approval, or production readiness.

## Fix before continuing local acceptance

1. **Resume the API and document worker, then restart the project-owned services.** The supervisor status currently reports the API and worker as `paused` and `private-data/runtime/maintenance` exists. The web, LAYA, indexer, and DOGC services show running, but the served processes may not include the latest changes. Until resumed and restarted, uploads, search, and document processing may not work reliably.
2. **Expose the agreed search modes in the interface.** The search page has a `scope` state and submits it, but the inspected UI does not render a control to select `normative`, `all_publications`, or `attachments`. The default remains normative, so users cannot deliberately choose Todas las publicaciones or Buscar en documentos adjuntos from this page. Add clearly labelled mode controls and test each mode.
3. **Fix and rerun two newly added focused regressions.** Latest result: `2 failed, 2 passed` in `tests/ops/test_document_processing.py` and `tests/integration/test_attachment_search.py`.
   - `completion_dimensions()` does not accept or account for an incomplete/failed source period, even when expected and integrated counts match. A period marked partial/unavailable must block processing completion.
   - Private attachment retrieval checks whether a document has *any* passage-index row. It misses an incomplete index when part of a file has been indexed already; it then omits `PRIVATE_INDEX_PENDING`. Determine completeness against the expected passages/current model revision or the active index job, not simply the presence of one row.
4. **Resolve the repair-script bug before any restore rehearsal.** `scripts/rehearse_restore.py` previously referenced undefined `state['document_id']` inside `purge_and_verify`; it has been corrected to use the `document` argument in the working tree but the rehearsal has not yet been rerun against that correction.
5. **Correct inconsistent trash wording in existing documentation and UI.** The user-approved action is Mover a Papelera, recoverable indefinitely, with permanent deletion as a separate explicit action. Some user documentation still describes Eliminar documento followed by immediate revocation/purge. Make the library, document detail, and guides agree on reversible trash versus irreversible permanent deletion.
6. **Fix damaged Spanish UI text and verify encoding.** Several edited UI strings currently contain literal question marks where accented characters or punctuation should appear (for example in the search refinement and attachment result labels). Run a UTF-8/source scan and visually inspect the built interface.

## Features present in code, but still need end-to-end proof

- Library folders, notebooks, document listing, rename/move, notes with revisions, saved legal-version references, trash, restore, and permanent-delete routes/components are implemented. Backend PostgreSQL tests previously passed for tenant isolation, notes, revision conflicts, trash/restore, deletion, and processing. The full requested browser workflow (upload, folder, notebook, save/edit/reload notes and references, trash/restore, empty trash, and reader permissions) has not been verified against the latest build.
- Uploaded PDF preview, DOCX extracted text/download, exact legal-version reader, official-PDF asset reader, and source links are implemented. A real Constitution original PDF was captured. Many official original PDFs are not captured; each missing original must be shown as unavailable. The former browser report tested the earlier upload/selection/delete flow, not the latest Papelera workflow.
- Optional query refinement, semantic retrieval, bounded multi-file attachment handling, private document retrieval, and evidence-based retrieval explanations are implemented in API/graph code. The latest frontend still needs working scope controls, clear grounding labels, and a current two-attachment browser flow. Recheck Unicode passage offsets and target-page selection in the reader.
- LAYA is invoked in shadow mode for the official-candidate flow, with baseline fallback on outage. It does not control production ranking. Do not describe a result as LAYA-ranked. Private-document retrieval uses its lexical/semantic path and does not establish legal applicability.
- The BOE/BORME summary adapters and daily/checker scripts exist. The script has imported a deliberately small bounded sample; this does not establish complete processing of either bulletin.
- The restore rehearsal framework exists and an earlier synthetic private-schema restore report passed, but the current schema/code changes have not had a fresh rehearsal. The earlier report did not establish full legal corpus/Auth restoration, journal replication, key custody, or 30-day backup expiry.

## Release blockers that require source work or human evidence

- **Nationwide official-publication coverage:** the latest saved processing report is blocked for 77 required sources and 8,213 required jurisdictions. The checked report listed 214 catalogue items, only 4 integrated items, 97 bulletin passages awaiting embeddings, and 1,426,793 consolidated passages awaiting embeddings. These are report snapshots, not live counts. Its file-integrity run checked 14,359 archived files, but integrity alone does not establish source completeness.
- **All publication types, sources, annexes, and history:** regional, provincial, municipal, island and foral adapters and reconciled catalogues/history are incomplete. BOE/BORME ingestion does not yet enumerate and prove every required bulletin item, attachment, annex, and sub-item. Current and officially available historical ranges need independent source-by-source audit. Do not report all Spain complete while any required scope is unknown.
- **Professional evaluation and ranking decisions:** provide at least 200 lawyer-reviewed cases spanning Spanish, Catalan, Galician and Basque, jurisdiction levels, temporal/negative cases and misleading/no-document cases. Freeze quality and performance thresholds after the hardware pilot. No professional approval is currently evidenced. LAYA training is not authorized by the available evidence; first compare reviewed baseline/query-plan results and train only if there is a demonstrated classifier deficiency and held-out improvement.
- **Production operations:** local operation is not production. Complete deployment configuration (including optional domain/HTTPS), production authentication and authorization review, private object storage, malware scanning, encrypted backup/restore and deletion rehearsals, key custody, backup expiry evidence, licensing approval, and operational monitoring. The approved retention policy is keep until the tenant deletes; trash remains recoverable until manual permanent deletion.
- **Performance and search quality:** measure real BGE-M3 and LAYA behavior on target low-cost hardware. Set and freeze response-time, recall/ranking, negative false-positive, and index-freshness thresholds before the release evaluation. Semantic nearest neighbors must not be described as applicable law without reviewed evidence.
- **Human documentation:** complete and reconcile the app guide, developer guide, operator guide, architecture diagrams and feature explanations with the current Spanish UI and the trash/publication/search behavior.

## Evidence checked

- An earlier full Python run: **105 passed**. It predates the latest two added focused regressions; their latest run is **2 failed, 2 passed**, with failures described above.
- An earlier Next.js typecheck and production build passed before the latest UI/reader edits. Rerun both after fixing the Spanish strings and search-scope controls.
- A previously saved browser report passed the then-current login, official text search, PDF upload/extraction and selected-text search flow; it is not evidence for the latest full workspace workflow.
- Current supervisor status: API and worker paused; the saved processing report is blocked/stale for required nationwide sources. No fresh browser run, corrected restore rehearsal, 200-case professional evaluation or national source audit is recorded here.

## Suggested order

1. Resume/restart local services and verify health without changing or deleting the database.
2. Fix the two focused regressions; fix scope selector, trash wording, Spanish encoding, Unicode offsets and partial-index progress signals.
3. Run Python checks, TypeScript typecheck, production build, current browser flows, real model checks and restore rehearsal; record results and limits.
4. Continue bounded source/catalogue ingestion and source audits; keep the nationwide release blocked until all required sources and histories pass.
5. Complete professional review, frozen thresholds, production operations and human documentation.
