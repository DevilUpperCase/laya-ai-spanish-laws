# LAYA Jur?dico

Local legal-text search using mandatory **FastAPI, LangChain Core, LangGraph and real local LAYA**, with local BGE-M3, self-hosted PostgreSQL/pgvector and Supabase Auth, and a Spanish Next.js interface. No generative LLMs. Nationwide production release remains blocked by the confirmed coverage/review/operations requirements.

Open **http://127.0.0.1:3000**. Sign in with the email/password from ignored `private-data/login-credentials.json`. The manual tenant/token form has been replaced. Sessions use revocable HttpOnly cookies and survive refresh until expiry. Keep credentials private; after changing your password the bootstrap file is stale.

The limited Windows logon task starts the local supervisor automatically. The current-user encrypted backup task runs at 03:00 while signed in. The existing installation is configured; no setup scripts are needed to log in.

## Human documentation

- [Application guide](docs/APP_GUIDE.md): what the app does, login, search, dates/warnings, private documents, deletion and troubleshooting.
- [Operator guide](docs/OPERATOR_GUIDE.md): startup/status, initial setup, credentials, source imports, indexing, scanner/TLS, backup/restore and verification.
- [Developer guide and diagrams](docs/DEVELOPER_GUIDE.md): architecture, authentication, search, ingestion, deletion, roles and extension points.
- [Full owned-code reference](docs/CODE_REFERENCE.md): every owned code/configuration/test module and its interfaces.
- [Source-extension guide](docs/SOURCE_EXTENSION.md): audited publisher adapters and finite reviewed HTML/PDF manifest imports.
- [Optional domain hosting](docs/HOSTING_GUIDE.md): local defaults and a prepared host-Caddy/domain profile.
- [Lawyer/staff review workflow](docs/HUMAN_REVIEW_GUIDE.md): how the actual user records legal/source acceptance.
- [Remaining release work](docs/REMAINING_WORK.md): implemented evidence, unmet gates and the responsible human roles.

## Commands

Run from this folder in PowerShell:

```powershell
.venv/Scripts/python.exe scripts/local_stack.py status
.venv/Scripts/python.exe scripts/local_stack.py start
.venv/Scripts/python.exe scripts/local_stack.py stop
.venv/Scripts/python.exe scripts/runtime_report.py
.venv/Scripts/python.exe scripts/verify_package.py
.venv/Scripts/python.exe scripts/verify_package.py --release
```

Stop affects project-owned application processes and retains database volumes. The release check is expected to fail until substantive reviewed evidence is present. Dependency health is distinct from nationwide release readiness.

## Current implementation and evidence

All 45 earlier BOE import failures were reconciled from official originals. The database contains 12,440 instruments and 694,479 section versions (observed 2026-10-12); exact dated counts are in [runtime.json](verification/reports/runtime.json). DOGC/DOG imports are real but partial; all 14 DOGC preview gaps were recovered and the full DOGC catalogue backfill is running. The actual geographic inventory contains 8,213 entities, all awaiting reviewed normative coverage. Sources and observed counts do not prove national completeness.

Vector backfill runs with immutable real weights, current versions first and then history. Text search is available; semantic indexing remains partial. LAYA is integrated and invoked in shadow mode with warned baseline fallback. Ranking activation requires its separate reviewed comparison.

Normal-login browser search/upload/selection/deletion/logout passed against the real application/database. A real encrypted private-schema restore rehearsal passed deletion-barrier/access-denial/purge checks. A four-language development hardware pilot was measured without freezing thresholds. The 200 prepared review cases are **unreviewed drafts**. Production server/domain/TLS, independent backups/journal/key custody, elapsed expiry, complete nationwide source/history audits and licensing approval remain open.

See [runtime](verification/reports/runtime.json), [BOE recovery](verification/reports/boe-reconciliation.json), [browser check](verification/reports/browser-check.json), [test results](verification/reports/pytest.xml), [restore rehearsal](verification/reports/restore-rehearsal.json), [hardware pilot](verification/reports/hardware-pilot.json), [national review queue](sources/nationwide-review-queue.csv) and [implementation ledger](docs/IMPLEMENTATION_PROGRESS.md).

The original planning specification/contracts and Spanish prototypes remain design records. The actual implementation uses `db/migrations`, `services/api/app`, `services/ingest/ingest`, `apps/web` and the current operator/developer guides. `db/001_base.sql`, prototype examples and FakeRouter are not runtime model or production evidence.
