# Remaining issues and feature status

**Project:** LAYA_Juridico_Codex_2026  
**Status checked:** 12 October 2026, local development  
**Purpose:** Separate features already present in the code from features that are incomplete, unverified, or blocked. Implemented in code does not mean nationwide coverage, professional legal approval, or production readiness.

## Local acceptance issues resolved

1. **Local services resumed and checked.** The supervisor reports API, worker, web, LAYA, indexer and DOGC as `running`; `GET /health` returned 200. The web service restarted after the UI build.
2. **Search scopes are selectable and verified.** The Spanish search page exposes Normativa, Todas las publicaciones and Documentos adjuntos, submits `normative`, `all_publications` and `attachments`, and keeps normative as the default. Attachment search remains disabled until a ready document is selected. The latest real-browser report exercises all three scopes.
3. **Both backend regressions are fixed.** Processing completion now requires reconciled complete source periods. Private retrieval checks expected passage IDs at the active embedding revision and keeps lexical fallback available when an index is incomplete or has an active retry/failed job. Focused regression coverage and the full suite pass.
4. **The isolated restore rehearsal passes on the saved encrypted snapshot.** The rehearsal applies the current private-schema recovery migrations in its isolated database, reapplies the deletion journal, denies restored reads/downloads, invalidates restored browser sessions, and purges the restored canary object. The scoped report is `verification/reports/restore-rehearsal.json`; its live purge timing is null because the interrupted first stage did not preserve that measurement.
5. **Trash language matches behavior.** The guide and UI distinguish indefinitely recoverable Papelera from separately confirmed permanent deletion. Immediate access revocation and the 24-hour live-copy/30-day encrypted-backup clocks begin only with permanent deletion.
6. **Damaged Spanish UI strings and scope controls were checked.** Literal replacement question marks in the affected UI text were repaired. A UTF-8 source scan and visual inspection of desktop, mobile and coverage screenshots showed readable Spanish and no mobile horizontal overflow.

## Features present in code, with current end-to-end evidence

- Library folders, notebooks, document listing, rename/move, notes with revisions, saved legal-version references, trash, restore, permanent deletion, session refresh and logout were exercised in the current browser flow. The browser used synthetic private documents; the database integration tests cover reader write-denial and tenant isolation.
- PDF preview, DOCX extracted text, Unicode extraction, non-ASCII selection offsets and cited-page navigation were checked against the real local app. The test report records exact selected code-point spans and page navigation. Official original-PDF capture remains incomplete; a missing original must still be shown as unavailable.
- Optional query refinement, semantic retrieval, bounded multi-file attachment handling, private document retrieval and evidence-based retrieval explanations remain implemented in API/graph code. The current UI exposes explicit search scopes. Private-document retrieval does not establish legal applicability.
- LAYA runs in shadow mode for the official-candidate flow with baseline fallback on outage. It does not control production ranking. Do not describe a result as LAYA-ranked.
- BOE/BORME summary adapters and daily/checker scripts exist. The bounded sample import does not establish complete processing of either bulletin.

## Release blockers requiring source work or human/external evidence

- **Nationwide official-publication coverage:** the last saved processing snapshot reports 77 required sources and 8,213 required jurisdictions blocked. It listed 214 catalogue items, 4 integrated items, 97 bulletin passages and 1,426,793 consolidated passages awaiting embeddings. These are dated snapshot counts, not live totals. Its file-integrity run checked 14,359 archived files; file integrity alone does not establish source completeness.
- **All publication types, sources, annexes and history:** regional, provincial, municipal, island and foral adapters and reconciled catalogues/history remain incomplete. BOE/BORME ingestion does not enumerate and prove every required bulletin item, attachment, annex and sub-item. Current and officially available historical ranges still need independent source-by-source audit. Do not report all Spain complete while any required scope is unknown.
- **Professional evaluation and ranking decisions:** at least 200 lawyer-reviewed cases are required across Spanish, Catalan, Galician and Basque, jurisdiction levels, temporal/negative cases and misleading/no-document cases. Freeze quality and performance thresholds after the hardware pilot. No professional approval is evidenced. LAYA training is not authorized by the available evidence; first compare reviewed baseline/query-plan results and train only if a demonstrated classifier deficiency and held-out improvement justify it.
- **Production operations:** local operation is not production. Production identity/auth review, private object storage, malware scanning, encrypted backup/restore and deletion rehearsals, key custody, elapsed backup expiry, licensing approval and operational monitoring remain pending. The current restore report does not cover the legal corpus or Auth database, independent journal replication, key custody or 30-day elapsed expiry.
- **Performance and search quality:** measure real BGE-M3 and LAYA behavior on target low-cost hardware. Freeze response-time, recall/ranking, negative false-positive and index-freshness thresholds before release evaluation. Semantic neighbors must not be described as applicable law without reviewed evidence.
- **Human documentation:** complete user acceptance/training and keep the app, developer and operator guides, architecture diagrams and feature explanations aligned as deployment or audited scope changes.
- **Package release barrier:** the offline package checks pass, but the release evaluator still reports 22 blocked gates. These require real artifacts/attestations; local checks do not supply them.

## Evidence checked

- `python -m pytest -q --junitxml=verification/reports/pytest.xml`: **107 passed in 93.33 seconds**. The API and document worker were paused during this run to avoid a competing-worker race and resumed in the command's `finally` block. An earlier run also passed all 107 in 54.30 seconds.
- Focused processing, attachment-search, document and library integration tests: **11 passed**. This covers partial/unavailable/unknown source periods, incomplete or stale private indexes and adjacent document workflows.
- `npm.cmd run typecheck` and `npm.cmd run build`: passed.
- `verification/reports/browser-check.json`: passed at `2026-10-12T17:48:46.225Z`; the real API/database browser run covered login, workspace selection, three scopes, coverage warning, responsive layout, folder/notebook/notes/reference, PDF and DOCX, Unicode selection, attachment search/page navigation, trash preview/restore/permanent deletion, empty trash and logout.
- `verification/reports/restore-rehearsal.json`: passed at `2026-10-12T18:19:39Z` for an encrypted synthetic private-schema restore and deletion canary. The report states the limits above and records `live_purge_seconds: null`.
- `python scripts/verify_package.py`: offline package, traceability and verifier checks passed; release status is blocked with 22 gates. `python scripts/verify_package.py --release` exited 1 with the same 22 unmet gates, as required while real release evidence is absent.
- `GET /health`: 200; all six supervised local services were `running` after the test run. UI screenshots were inspected for desktop, mobile and coverage.

## Suggested next order

1. Continue bounded source/catalogue ingestion and independent source audits; leave nationwide release blocked until required sources and histories pass.
2. Complete professional review, frozen thresholds, production operations, licensing approval and human acceptance/training.
3. Refresh dated runtime/evidence snapshots as those activities progress; do not treat local acceptance results as closing any national or human-evidence gate.
