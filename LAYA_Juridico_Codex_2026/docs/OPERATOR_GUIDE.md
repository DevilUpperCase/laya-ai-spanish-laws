# Operating the local workspace

The current deployment is a single-user Windows development installation. All listeners are loopback. It is not a nationwide production release. Run commands from `LAYA_Juridico_Codex_2026` in PowerShell; use `npm.cmd` where PowerShell execution policy blocks npm.ps1.

## Daily operation

The limited current-user Windows task **LAYA Juridico Local** starts the supervisor after Windows sign-in. It starts/adopts only processes belonging to this project's scripts and working directories, starts the separate Docker services, retries failures with backoff, runs daily seven-day BOE reconciliation and resumes current-first/historical vector indexing and the full DOGC original-publication backfill. It never takes ownership of an unrelated listener.

```powershell
.venv/Scripts/python.exe scripts/local_stack.py status
.venv/Scripts/python.exe scripts/local_stack.py start
.venv/Scripts/python.exe scripts/local_stack.py pause
.venv/Scripts/python.exe scripts/local_stack.py resume
.venv/Scripts/python.exe scripts/local_stack.py stop
```

Pause suspends the private API and document worker for storage consistency; web/LAYA/indexing remain alive. Stop terminates owned application processes and retains database/container volumes. Resume requires the supervisor running. Status reports process state; HTTP health and model checks provide stronger operational evidence. A `running` process is not proof that its model is ready.

| Component | Local endpoint | Purpose |
|---|---|---|
| Next.js | 127.0.0.1:3000 | Spanish UI and same-origin API gateway |
| FastAPI | 127.0.0.1:8000 | Authorization, search, documents, coverage |
| LAYA | 127.0.0.1:8001 | Local classification in shadow mode |
| Supabase Auth | 127.0.0.1:9999 | Local password verification; signup disabled |
| PostgreSQL/pgvector | 127.0.0.1:15432 | Isolated application/auth databases |
| ClamAV | 127.0.0.1:13310 | INSTREAM malware checks |
| Caddy | https://localhost:8443 | Local TLS rehearsal |

`GET /health` measures API liveness. Internal authenticated `/ready` distinguishes dependencies from release readiness and deliberately returns 503 while mandatory release evidence is missing. Do not remove coverage/evaluation gates to make readiness green.

## Reproduce setup on an empty installation

Prerequisites: Windows, Python 3.12, uv, Node 22, Docker Desktop, adequate disk/RAM, and network access to approved public artifact sources. The existing machine is already initialized; **do not reset its volumes or rerun the full catalogue just to log in**.

```powershell
uv sync --frozen --extra models
.venv/Scripts/python.exe scripts/setup_docker.py
.venv/Scripts/python.exe scripts/download_models.py
.venv/Scripts/python.exe scripts/download_ocr.py
.venv/Scripts/python.exe scripts/create_local_session.py
.venv/Scripts/python.exe scripts/setup_auth.py
Push-Location apps/web
npm.cmd ci
npm.cmd run build
Pop-Location
.venv/Scripts/python.exe scripts/local_stack.py start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install_autostart.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install_backup_schedule.ps1
```

The container bootstrap uses pinned image digests from `infra/*.compose.yaml`, existing ignored `private-data/auth.env` and a separate `laya-juridico-development` network. Never delete another application's database or the native PostgreSQL installation. Migrations are checksum-tracked and transactional; add a new migration instead of editing an applied one.

## Credentials and account operations

`private-data/login-credentials.json` contains the generated initial email/password; normal login requires no developer token. After a password change this file is stale and should be protected or removed after secure recording. Setup preserves an existing account and does not reset its password. Existing browser-test scripts use the bootstrap credentials and must be supplied a dedicated valid test account before running after an owner password change.

`private-data/local-session.json` is a short-lived RS256 automation/development session. It is not a browser-login requirement. `create_local_session.py` renews a development session for the existing local identity; do not share its token. Auth verification keys, database credentials, API keys and `.env` stay ignored. Production must manage identities, invitations/recovery, account suspension and key rotation explicitly; public signup is disabled.

API/ingest/worker roles have separate credentials. The Auth role only owns the isolated `laya_auth` database. API requests resolve trusted identity plus live tenant membership; a tenant header is never sufficient. Private tables use FORCE RLS. Admin credentials are limited to maintenance CLI operations.

## Sources, history and indexing

```powershell
.venv/Scripts/python.exe scripts/reconcile_boe_gaps.py
.venv/Scripts/python.exe scripts/sync_boe.py
.venv/Scripts/python.exe scripts/sync_dogc.py --limit 10
.venv/Scripts/python.exe scripts/sync_dog.py
.venv/Scripts/python.exe scripts/audit_publishers.py
.venv/Scripts/python.exe scripts/coverage_workqueue.py
.venv/Scripts/python.exe scripts/database_status.py
```

The 45 targeted BOE failures are resolved in `verification/reports/boe-reconciliation.json`. The original population report remains a dated record of its earlier failures. BOE consolidation is not every Spanish publisher's complete normative archive. The 14 earlier DOGC preview gaps were recovered in dogc-reconciliation.json by retaining available official language text and warning about missing variants. The supervised DOGC backfill enumerates the full 31,125-record observed catalogue with an exclusive writer lock and skips already committed original instruments on restart. Skipping existing originals does not refresh historical variants/corrections and is not coverage proof. Read its durable legal.ingest_runs progress while the full job runs.

DOGC and DOG reports remain partial; RSS previews do not cover available history. Publisher reachability audits archive entrypoints and candidate feeds, not jurisdiction completeness.

`sources/nationwide-review-queue.csv` lists all 8,213 imported geographic entities for independent source/current/history review. Exporting again currently overwrites the generated queue: copy human work to a separate reviewed artifact before regenerating. The INE island workbook's internal date and the institutional foral supplement still need reconciliation. Use the source-audit template and the release validator; do not mark a jurisdiction verified from an observed count.

For a publisher without a complete discovery adapter, a reviewed publication manifest can import enumerated normative HTML/PDFs through `scripts/ingest_manifest.py`. See [SOURCE_EXTENSION.md](SOURCE_EXTENSION.md). This helps regional/provincial/municipal/island/foral imports while explicitly retaining archive-completeness gaps.

The supervised indexer acquires an exclusive database advisory lock and prioritizes current versions before history. Committed vectors survive restart. Every vector is tied to the immutable BGE revision; a different model requires intentional reindexing. Progress/rate/ETA are in `verification/reports/index-progress.json`. On this CPU, full historical indexing can take many weeks. Do not start a second indexer or report semantic completeness while passages are missing. `--include-history` is the supervised setting.

## Malware scanning and TLS

ClamAV uses persistent signature volumes and container health checks. Uploads fail closed when configured scanning cannot complete. The EICAR regression uses a harmless standard test signature. Monitor signature freshness and scanner health before accepting real client uploads.

Caddy's local CA certificate is in `private-data/auth/local-tls-root.pem`. It was used to verify local HTTPS; it has **not** been installed in Windows' global trust store. Browsers may show a certificate warning at localhost:8443. The normal development address remains port 3000. Do not distribute or weaken certificate validation to conceal the warning.

`infra/Caddyfile.production` is a deployment template. A real server/domain, DNS, firewall, secure cookie configuration, trusted proxy design and approved production identity management are still needed. Do not expose PostgreSQL, Auth admin access, ClamAV or LAYA publicly.

## Encrypted snapshots and restoration

The task **LAYA Juridico Encrypted Backup** runs daily at 03:00 while this Windows user is signed in. It does not catch up a missed run automatically. It briefly pauses API/worker, encrypts streamed PostgreSQL dumps and storage archives, then resumes services and expires authenticated snapshots older than 30 days. Check `verification/reports/scheduled-backup.json` after each run. A stopped supervisor or existing manual maintenance makes the run fail/defer visibly.

```powershell
.venv/Scripts/python.exe scripts/scheduled_backup.py
.venv/Scripts/python.exe scripts/backup_local.py expire
.venv/Scripts/python.exe scripts/rehearse_restore.py
```

These commands can pause the private API during a snapshot. Allow sufficient time/disk: the full legal corpus is large. No plaintext dump/archive is written to disk; ciphertext is block-authenticated AES-256-GCM with an authenticated end marker, and the manifest authenticates file hashes. The key is `private-data/backup-keys/master.key`; losing it loses access to snapshots. **The key and backups are currently on the same host.** Independent encrypted replication, separate key custody and monitoring are mandatory production work.

The restore rehearsal creates a synthetic PDF, snapshots it, deletes/purges it live and restores private schemas/storage into an isolated `laya_rehearsal_<hex>` database. It authenticates ciphertext before restoring, initializes pgvector/schema prerequisites, reapplies the current independent deletion journal, invalidates restored browser sessions and checks denied reads/downloads plus actual restricted-worker purge. It never restores over the live database. The passed report covers private schemas and a synthetic canary; it does not prove full public-corpus/Auth recovery or 30 days of elapsed retention.

Retention issues are recorded in `verification/reports/backup-retention.json`. Interrupted/untrusted snapshots are preserved for safe operator cleanup and do not prevent authenticated expiry of other snapshots. Review those alerts; preserving an incomplete snapshot is not proof of the retention deadline. Retention runs even if today's snapshot fails.

A failed restore retains ignored `private-data/runtime/restore-state.json` and its isolated target for diagnosis. `--resume` is suitable only before that target has committed restoration; a target already restored requires diagnosis/continuation or an intentional new isolated rehearsal. Never rerun a restore against the production database. Delete isolated copies only after validating exact owned database/path identity.

Before any production restore serves traffic: obtain the **latest independently replicated deletion journal**, restore into isolation, replay all records regardless of old purge completion, invalidate sessions, purge restored deleted objects/text/vectors, verify access denial, then perform the separately approved switch. Restoring a stale deletion journal is insufficient.

## Evaluation, licenses and verification

`evaluation/review-queue.json` contains 200 drafts covering four languages and five territorial strata. They are not reviewed judgments. Professionals must choose exact jurisdictions, references, dates, relevance grades and independent review evidence. `python -m evaluation.pilot` measures public latency without freezing policy. `evaluation.freeze_policy` requires reviewed cases, a successful measured pilot, numeric thresholds and acceptance evidence; its receipt needs independent immutable custody **before** collecting holdout rankings.

`scripts/license_inventory.py` collects observed Python/Node license metadata and artifact hashes, model/OCR records and container configurations. No license approval is inferred. PyMuPDF distribution/license choice and publisher reuse terms require explicit human clearance.

```powershell
.venv/Scripts/python.exe -m pytest -q --junitxml=verification/reports/pytest.xml
.venv/Scripts/python.exe scripts/prepare_browser_fixture.py
node tests/e2e/browser-check.cjs
.venv/Scripts/python.exe scripts/runtime_report.py
.venv/Scripts/python.exe scripts/verify_package.py
.venv/Scripts/python.exe scripts/verify_package.py --release
```

The last command is expected to fail while release evidence is missing. Preserve that result. The ordinary package check verifies package consistency; tests verify behavior; professional/source audits verify different obligations. Consult [REMAINING_WORK.md](REMAINING_WORK.md) for owners and required evidence.
