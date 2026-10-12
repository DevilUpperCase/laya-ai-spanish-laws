# Local development operations

Current operational instructions, normal login, supervisor, scanner/TLS and backup rehearsal are in [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md). Older manual-token/startup instructions below are historical and superseded.

The Docker database is a separate development database at 127.0.0.1:15432.
Only the database runs in Docker; API, worker, models and Next.js run locally.
The named development bridge permits port forwarding; it is not a production
egress restriction. No public deployment is authorized or claimed.

Secrets live in ignored `.env` and `private-data`. Never print the connection
URLs, Docker secret files, RSA private key, or local session token. Generate a
new session with `scripts/create_local_session.py`; it creates only a local
development tenant and a short-lived RS256 token. Browser credentials are
memory-only. Production requires reviewed self-hosted authentication,
membership administration, TLS, scanner, egress controls and backup operations.

Use Python 3.12 with the checked-in uv lock and npm lock. `setup_docker.py`
starts the dedicated volume, creates restricted roles and applies checksum-
tracked migrations. Running it again preserves existing database records.
Migration scripts are forward-only. Preserve a consistent encrypted snapshot
before a production migration; test recovery in a separate database. Do not
delete the development Docker volume to rerun migrations.

LAYA's multilingual checkpoint and BGE-M3 are pinned by immutable revisions
and SHA256 manifests. Their local loaders prohibit remote custom code and
runtime downloads. Readiness remains HTTP 503 even with healthy runtime
dependencies because national audits, professional evaluation and operations
rehearsal remain outstanding. Search preserves baseline order in shadow mode
and warns on unavailable/incomplete classification or partial vector indexing.

`populate_database.py --boe-limit N` imports the first N integrated catalogue
records, preserving originals, versions, dates, hashes and explicit gaps.
Replays are idempotent; a bounded run never advances complete-source freshness.
`--boe-all` processes the full BOE consolidated catalogue and can take a long
time. It cannot establish national coverage: municipal/provincial/island/foral
publishers still need approved adapters and current/history reconciliation.
`sync_boe.py` reconciles a rolling seven-day **source update-date** window;
configure a reviewed local scheduler only after a successful backfill and
monitor failed/partial runs. There is no automatic national scheduler claim.

`embed_corpus.py` can be resumed: it writes only missing pinned vectors. It
indexes current observed versions by default; historical keyword/reference
search is available without vectors. Historical vector indexing is a separate
backfill. CPU-only embedding is slow on this host. Measure a hardware pilot
before freezing launch latency/quality thresholds.

PDF/DOCX processing runs in bounded child processes. Development has no
ClamAV service configured; production configuration refuses a missing scanner.
Local OCR is now enabled with pinned spa/cat/eus/glg artifacts installed by
scripts/download_ocr.py. Image-only Spanish PDF extraction, uncertainty flags
and scanned-upload worker processing passed real local tests. Review OCR
accuracy across supported languages and real client formats before launch.
If disabled, scanned PDFs explicitly return OCR_REQUIRED.
Private page selections are checked against stored Unicode code-point offsets;
client-supplied replacement text cannot be used as document evidence.

See [backup and restore contract](../infra/backup-policy.md) for deletion-barrier
procedures. Monitor worker failures, five-minute stale leases, and any purge
over 24 hours. Development commands do not certify backup compliance, scanner
effectiveness, accessibility, legal accuracy, or dependency/source licensing.
