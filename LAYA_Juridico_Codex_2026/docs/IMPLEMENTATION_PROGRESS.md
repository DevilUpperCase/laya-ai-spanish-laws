# Implementation ledger

Plans: docs/superpowers/plans/2026-10-11-01-foundation.md through -04-release-operations.md.
Spec: docs/SPECIFICATION.md. Implementation authorized 2026-10-12.

## Decisions

- Ruling: use this existing project directory as the isolated workspace. It has no Git repository, so Git worktree/commit helper commands cannot apply. Preserve the ledger and tests here; no existing repository or database is modified. Cost: changes have no Git rollback until the owner initializes a repository.
- Ruling: requested execution subskills and helper scripts are absent from both installed skill directories. Follow failure-first tests and recorded verification directly. Cost: helper automation is unavailable.
- Ruling: the owner explicitly chose Docker Desktop. Use a separate PG17/pgvector development container, loopback port 15432, independent volume and restricted roles. The native-cluster proposal was superseded; no native cluster was started. Cost: this is not production Supabase/auth/backup deployment.
- Ruling: professional legal review, per-publisher audits, national backfill, hardware thresholds, and backup-expiry proof cannot be invented by code. Implement their tooling and leave unmet release gates blocked. Cost: internal application progress is not nationwide launch readiness.

## Interface pre-flight

| Producer -> consumer | Agreed boundary |
|---|---|
| F1 -> F2/F3/S2/S4 | Pydantic contracts, validated settings, explicit tenant context |
| F2 -> S1/C1 | Versioned legal tables and separate corpus writer |
| F2/F3 -> O1/S4 | Composite tenant/document IDs; tombstone and deletion epoch checks |
| S1 -> S2/C3 | Original hashes, publication/version identity, no inferred effective dates |
| S2/S3 -> S4/F4 | LangChain runnable, validated shadow decisions, compiled ephemeral LangGraph |
| C1/C2/C3 -> O2/O3 | Inventory/source gaps remain explicit; complete requires independent review |

## Work

Inspection: Python 3.12 and 3.13, Node 22, uv, PostgreSQL 17, and MSVC Build Tools present. Docker engine unavailable. No project database credentials, models, application, or dependency lock existed.

Implemented F1/F2/F3/F4 development behavior: typed FastAPI routes, local RS256 membership authentication, restricted API/ingest/worker roles, forced RLS/composite tenant parent keys, bounded PDF/DOCX processing, tenant-authorized stored selections, revocable downloads, durable extraction/purge jobs and Spanish Next.js UI. Production hosting/auth administration/scanner/OCR remain outstanding.

Implemented S1/S2/S3/S4 development behavior: actual official XML/provenance/history storage, FTS/reference/title-trigram/pgvector retrieval, actual LangChain Core runnable and ephemeral LangGraph, actual local BGE-M3 and LAYA weights, strict shadow/fallback policy and literal evidence explanations. CPU vector indexing remains partial; historical vector backfill and professional relevance gates remain outstanding.

C1/C2/C3 partial: 8,213 real official geographic entities, 73 directory/source entries, and a bounded BOE import with 121 instruments, 23,695 section versions and 47,664 chunks. The 120-record catalogue run is partial by design with zero jurisdiction-resolution gaps. Inventory review, island workbook date mismatch, foral supplements, publisher adapters and every jurisdiction's current/history audit remain outstanding. These numbers are observed development counts, not verified national coverage.

O1/O2/O3 partial: explicit deletion intents are fsynced independently of database/object snapshots before acknowledgement; replay resets completed purge jobs safely. Metric tooling requires reviewed cases and frozen policy receipts, with a maximum negative-case false-positive rate. Professional review, freeze authenticity, production backup encryption/expiry/replication, actual restore rehearsal and capacity evaluation remain outstanding; G01..G22 evidence is not marked passed.

Ruling: npm's lockfile and standard shadcn/Radix primitives implement the existing UI direction. Cost: original pnpm examples are adapted to npm commands. Ruling: local development storage is a revocable filesystem gateway; production Supabase storage/auth integration still needs deployment evidence.

Observed checks: full pytest suite 60 passed after review fixes, including real PostgreSQL isolation/deletion/restore replay and real LAYA inference. Next.js typecheck and production build passed. Real Chrome browser flow passed: corpus search/official links, visible coverage blocker, mobile overflow, PDF upload/durable extraction/stored-selection search/deletion. A synthetic private PDF is used; no professional legal or WCAG claim follows.

Final review: one fresh read-only gpt-6-astra reviewer, as required by executing-plans. Five Important findings were fixed in one pass: null LAYA envelopes, private endpoint boundary, effective-version selection, completed-purge restore replay, and negative-case metric gating. Added regressions; full suite green. No Critical finding reported. Plan completion boxes remain unchecked where their full external/production evidence contract is unmet.

Security correction: one failed development test emitted a Settings representation containing a generated database credential. Sensitive fields now use repr=False; all generated development credentials were rotated. No credentials appear in committed reports.

Current reports: verification/reports/database-population.json, runtime.json, browser-check.json and pytest.xml. Runtime dependencies may be healthy while HTTP /ready returns 503 because release is blocked.

Additional verification: 63 tests passed with no warnings after pinned local OCR setup. Actual image-only Spanish PDF OCR and scanned-document upload/worker/selection/download/deletion passed. Added a render-pixel budget tested before native OCR rendering. Language artifacts spa/cat/eus/glg have immutable revision/hash records in verification/ocr-artifacts.json; multilingual accuracy and license approval remain unverified. The final post-fix browser rerun passed against refreshed UI/API. The full BOE consolidated catalogue backfill and current-version embedding process continue locally; runtime.json is a dated count snapshot, not a completion claim.

## Completion work — 2026-10-12

The owner authorized direct implementation of the seven remaining areas. The completion plan is docs/superpowers/plans/2026-10-12-completion.md. No Git repository exists; retain this ledger and review reports instead of deleting the execution record. No live public deployment is authorized or configured.

Login: added real self-hosted Supabase Auth, restricted isolated auth database, opaque hashed HttpOnly browser sessions, strict Origin/custom-header checks, normal email/password UI, password change, session restore and logout. Generated account credentials remain only in ignored private-data/login-credentials.json. Two real Auth tests passed. Existing Auth migration metadata required reconciliation after search_path correction; fresh setup sets auth search_path before migrations.

Startup: added a single-owner supervisor with exact process/cwd ownership checks and maintenance pause/resume. Registered the limited current-user Windows logon task LAYA Juridico Local. Required loopback services and historical vector indexing are supervised; database containers are retained on stop. Runtime-lock regressions passed.

BOE: diagnosed all 45 captured failures. Exact issuer alias (39), unknown sentinel effective date (1), original-publication evidence for malformed mandatory dates (2), bounded 128 MB official source cap (3). All 45 were retried successfully; boe-reconciliation.json records zero outstanding targeted gaps. This is not a national source audit. Six login/gap regression tests passed.

Indexing: exclusive DB writer lock, current-first/history backfill, persistent progress/ETA and cached current-version IDs. Real CPU indexing remains partial and too slow to declare completion. Search scale regressions exposed generic prepared plans and common-query timeouts; forced custom plans, a dated atomic current-version cache and explicit degraded-engine warnings fixed the measured failures. Five scale/regression checks passed.

Sources: captured 73 official publisher entrypoints (35 captured, 38 transport/redirect failures at first audit). Implemented real DOGC open-data/Akoma Ntoso and DOG general-disposition RSS previews. DOGC imported 10 actual records with 14 failures; DOG imported one Spanish/Galician normative record. Discovery windows, missing translations/annexes and history remain explicit gaps. These do not approve any jurisdiction. Official HTTP compression/redirect regressions passed.

Operations: real pinned ClamAV with persistent signatures and a passing EICAR test; loopback Caddy HTTPS verified with its local CA certificate, without installing global trust. Added authenticated AES-256-GCM streaming snapshots, signed manifests and bounded expiry. Crypto tamper/wrong-key tests passed. Real encrypted snapshot completed; private restore initially failed because pg_restore schema filtering omits schema creation. Added explicit isolated schemas/pgvector initialization and resumed the existing snapshot. Restoration evidence was subsequently completed: see the passed scoped canary report and later ledger entry.

Ruling: no names, signatures, professional judgments, source completeness, production domain, licensing approval or elapsed backup expiry can be fabricated. Build review work queues and runnable gates; keep release false while external evidence and long-running backfill remain absent.

Current completion verification: full pytest 87 passed in 28.81 seconds after pausing the competing background document worker; Next.js typecheck and production build passed. The first full run found a test race and an environment-dependent missing-production-config assumption, corrected by coordinated worker pause and _env_file=None in that assertion. Real normal-login/refresh/search/upload/selection/delete/logout browser flow passed. Offline package checks passed and all 22 release gates remain blocked, intentionally.

Evaluation/source tooling: exported all 8213 current inventory entities and checked exact coverage-queue equality; zero independent coverage approvals. Generated 200 draft cases across four languages/five strata, none professionally reviewed. Eight actual public-query pilot requests completed with zero HTTP errors; p95 was 74217.33 ms including cold model loading and warned LAYA degradation. No thresholds were frozen. Negative cases no longer dilute positive stratum relevance metrics; unreviewed null reviewer records fail validation cleanly. Nine evaluation/encryption regressions passed.

Backup recovery: real encrypted snapshot and isolated private-schema restore passed after explicit schema/pgvector prerequisites and restored schema usage grants. The current deletion journal denied restored canary reads/downloads and the restricted worker removed its restored original. The resumed first run did not retain live purge timing; report states null rather than inventing it. Full public/Auth recovery, independent replication/keys and elapsed expiry remain pending. Daily encrypted snapshot task registered at 03:00 while the current user is signed in, coordinated maintenance and bounded expiry; no first scheduled run is claimed.

Source extension: reviewed finite HTML/PDF manifest importer supports exact existing geographic identities at every level with source-namespaced storage IDs, matching review hashes, exact official hosts, explicit normative selection and real isolated PDF extraction after scanner validation. This does not replace missing publisher discovery/history adapters. Synthetic PDF parser wiring and manifest review/host constraints passed. Human guides, diagrams and generated reference cover 146 owned code/config/test files; README links the current normal-login workflow and outstanding external obligations.

Licensing: collected 97 actually installed Python distributions and 109 Node lock entries, model/OCR evidence and pinned container configurations. All approvals remain pending. Fresh independent completion review is running; no release evidence is marked passed by these local checks.


Owner clarification: professional reviewers are the lawyer or designated lawyer employee who uses the app. No actual named reviewed dataset/audits are supplied. Hosting remains local now; downloaded copies should support a configurable domain later. Added HOSTING_GUIDE.md, validated configure_domain.py (prepare-only by default; apply is explicit) and HUMAN_REVIEW_GUIDE.md. No domain profile was applied or site published. Public holdout collection requires a reviewed dataset and matching independently recorded frozen policy hash, and refuses failed requests rather than treating them as negative results.

Fresh final implementation review found zero Critical and three Important issues: incomplete-backup retention blocking, identical-byte distinct manifest version loss and false process ownership from data arguments. Six targeted regressions were observed failing, then passed after the single material fix pass. Added migration012 for metadata-aware logical publications while preserving original SHA/legacy replay; locked key/snapshot creation and independent retention; exact interpreter script/module/Next start identity; retained Popen exit status to fix unintended successful-sync retries. The actual retention command completed safely with zero expired current snapshots.

Additional source recovery: all 14 captured DOGC failures resolved by retaining actual available language text with OFFICIAL_TRANSLATION_MISSING for an unavailable variant. Official XML with an empty language response is archived rather than fabricated. Captured diagnostic bodies prove the source-language issue. DOGC's observed official catalogue contains 31,125 records; 970.5 GiB free disk observed. Full original-publication backfill is supervised with an exclusive writer lock and explicit skip-existing-originals restart policy; source history/annex/language completeness remains unverified. Seven source/supervisor targeted tests passed.


Final current checks: 95 tests passed in 62.23 seconds with the competing private worker paused and resumed in finally; Next typecheck/production build passed; final real Chrome normal-login/refresh/public search/upload/extraction/stored-selection/deletion/logout passed at 2026-10-12T13:54:40Z. Documentation regenerated for 153 owned files. Offline package passed and all 22 unreviewed release gates remain blocked. Application services were resumed; full DOGC source backfill and current/history vectors remain supervised background work. Local default hosting retained; optional domain configuration was checked without applying it. Temporary CLI browser inspection session is closed.

Task completion boundaries: ordinary local login/startup and human documentation are implemented and verified. BOE45/DOGC14 targeted recovery is complete; full DOGC/vector runs are in progress. Additional complete regional/provincial/municipal/island/foral source adapters, national source/history/inventory approval, actual professionally reviewed evaluation/accepted frozen thresholds, license approval and full production/off-host/elapsed-retention evidence remain outstanding. These are not waived by the owner choosing local hosting.
