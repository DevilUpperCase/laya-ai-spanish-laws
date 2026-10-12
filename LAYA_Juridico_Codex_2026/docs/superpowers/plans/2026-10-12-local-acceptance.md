# Local Acceptance Backlog Implementation Plan

> **For agentic workers:** Execute these tasks in order in the existing project workspace. The owner has authorized implementation and local development operations; no public deployment is authorized.

**Goal:** Resolve the actionable local acceptance issues recorded on 2026-10-12, verify the latest app flows, and keep national-release evidence accurately blocked where human or external evidence is still missing.

**Architecture:** Keep official-publication processing and private attachment retrieval separate. Make completion depend on positively reconciled source periods and a complete current-revision passage index. Expose the existing explicit search scopes in the Spanish UI and preserve the reversible trash lifecycle.

**Tech Stack:** Python 3.12, FastAPI, PostgreSQL/pgvector, pytest, Next.js, TypeScript, Playwright/Chrome.

**Spec:** `docs/SPECIFICATION.md`; task evidence: `docs/REMAINING_ISSUES_AND_FEATURE_STATUS.md`, `docs/REMAINING_WORK.md`, and `docs/HISTORICAL_APP_REQUESTS.md`.

## Global Constraints

- Keep normative, all-publication, and private-attachment search scopes explicit and distinct.
- Never infer source completeness from matching local counts; unknown, partial, and unavailable periods block snapshot completion.
- Keep private attachment content tenant-scoped and do not claim an index complete from a nonempty passage row.
- Trash remains recoverable until a separate permanent-delete action; the 24-hour/30-day clocks begin at permanent deletion.
- Do not claim nationwide coverage, professional review, production readiness, or licensing approval without the required real evidence.

## Review Focus

- Matching counts with a partial, unavailable, or unknown source period must block completion; test in `test_document_processing.py`.
- A single indexed passage or non-current model revision must not mask missing passage-index work; test in `test_attachment_search.py`.
- Each visible search scope must submit its exact API value and attachments-only mode must require a selected file; verify in the real browser flow.
- Trash and permanent deletion must remain distinct in the UI and human guide; verify labels and the browser trash/restore flow.
- Unicode selections must retain exact Python/code-point offsets and requested page navigation; verify through document selection/search and the latest browser flow.

---

### Task 1: Resume local acceptance services

**Files:** No source changes. Runtime evidence may update `verification/reports/runtime.json`.

- [x] Resume the paused API and worker using `scripts/local_stack.py resume`.
- [x] Confirm supervisor reports API and worker as running and `GET /health` returns 200.

### Task 2: Require reconciled source periods for processing completion

**Files:** Modify `services/ingest/ingest/processing_status.py`; modify `tests/ops/test_document_processing.py`.

- [x] Reproduce the existing regression: `pytest tests/ops/test_document_processing.py -q` must show the unsupported `periods_complete` argument.
- [x] Add cases showing `partial`, `unavailable`, and unknown period states block a matching-count snapshot.
- [x] Implement a required positive period-completeness input and derive it from reconciled `complete` periods only.
- [x] Run `pytest tests/ops/test_document_processing.py -q` and confirm pass.

### Task 3: Detect partial or stale private passage indexes

**Files:** Modify `services/api/app/private_retrieval.py`; modify `tests/integration/test_attachment_search.py`.

- [x] Reproduce the existing regression: one ready document with a retrying index job returns no `PRIVATE_INDEX_PENDING` warning.
- [x] Compare expected passage IDs from stored page text with current-revision indexed passages, and treat unfinished/failed index jobs as incomplete.
- [x] Preserve lexical fallback over stored extraction for every incomplete document.
- [x] Test partial passage coverage and a stale embedding revision without an active job.
- [x] Run `pytest tests/integration/test_attachment_search.py -q` and confirm pass.

### Task 4: Expose search scopes and repair Spanish UI text

**Files:** Modify `apps/web/src/app/page.tsx`, `apps/web/src/lib/api.ts`, `tests/e2e/browser-check.cjs`.

- [x] Add accessible controls labelled Normativa, Todas las publicaciones, and Documentos adjuntos, bound to `normative`, `all_publications`, and `attachments`.
- [x] Keep attachments-only search disabled until at least one ready attachment is selected.
- [x] Replace damaged question marks in user-facing Spanish strings with valid UTF-8 text.
- [x] Verify selected mode is present in each real browser search request and that defaults remain normative.
- [x] Run web typecheck and production build.

### Task 5: Align trash guidance and verify reversible deletion

**Files:** Modify `docs/APP_GUIDE.md` and, if browser text exposes a mismatch, `apps/web/src/components/document-library.tsx`, `apps/web/src/app/documents/[id]/page.tsx`, `tests/e2e/browser-check.cjs`.

- [x] Explain that moving an item to Papelera is recoverable indefinitely; permanent deletion is separate and starts immediate access revocation, the live-copy 24-hour purge, and encrypted-backup 30-day expiry.
- [x] Verify move-to-trash, hidden-from-attachment search, trash preview, restore, and separately confirmed permanent deletion against the latest app.

### Task 6: Verify the isolated restore rehearsal

**Files:** `scripts/rehearse_restore.py` is already corrected; update `verification/reports/restore-rehearsal.json` only after a successful run.

- [x] Run `python scripts/rehearse_restore.py --resume` against the existing synthetic snapshot and isolated rehearsal database.
- [x] Confirm restored reads/downloads remain denied and the restored synthetic object is purged; retain the report's stated scope limits.

### Task 7: Recheck reader selection and current browser workflow

**Files:** Modify `tests/e2e/browser-check.cjs` and relevant UI code only if the current flow reveals a bug; update `verification/reports/browser-check.json` only from the run.

- [x] Verify a non-ASCII selection maps to the same stored code-point span and search results open the requested page.
- [x] Exercise the current upload, extraction, scope, search, trash, restore, logout/session and responsive layout paths using synthetic private data.
- [x] Run the real browser flow and inspect its screenshots and report.

### Task 8: Refresh status and retain release boundaries

**Files:** Update `docs/REMAINING_ISSUES_AND_FEATURE_STATUS.md`, `docs/REMAINING_WORK.md`, `docs/IMPLEMENTATION_PROGRESS.md`.

- [x] Record completed work and exact commands/results, and keep genuinely external or long-running national-release evidence pending.
- [x] Run `python scripts/verify_package.py`; report offline and release-gate outcomes separately.

