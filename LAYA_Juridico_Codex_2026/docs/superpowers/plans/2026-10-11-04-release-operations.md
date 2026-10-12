# Release Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove privacy/deletion, professional quality and reversible self-hosted operations before launch.

**Architecture:** Release is gated by real reviewed artifacts for every requirement. Hardware pilot and frozen holdout thresholds precede approval; deletion tombstones survive restoration.

**Tech Stack:** FastAPI, LangChain Core, LangGraph, local LAYA, BGE-M3, self-host Supabase/PostgreSQL/pgvector, Next.js/TypeScript.

**Spec:** `../../SPECIFICATION.md`; read the specification, contracts, acceptance matrix, and prerequisite plans before execution.

## Global Constraints

- Mandatory tools: FastAPI, LangChain Core, LangGraph, and local LAYA.
- No generative LLMs, external inference, private external tracing, or persisted private search graph state.
- Self-host Supabase/PostgreSQL, authentication, private storage, BGE-M3, and LAYA.
- Next.js + TypeScript + Tailwind + shadcn/ui; Spanish UI initially.
- Search/evaluation languages: es, ca, gl, eu.
- First release requires verified coverage for every required Spanish jurisdiction; internal milestones are not releases.
- Retain documents until tenant deletion; revoke access immediately, remove live copies within 24 hours, expire encrypted backups within 30 days, and reapply deletion records on restoration.
- Professional evaluation requires at least 200 queries; performance thresholds are frozen after a hardware pilot before launch evaluation.


## Review Focus

- Valid pre-deletion download links and queued workers must lose access immediately (O1).
- Restored backups cannot resurrect deleted text/vectors or cached derivatives (O1/O3).
- Canary text/query/secrets must not escape through error logs, tracing or job state (O1).
- Calibration leakage or missing language/territory strata invalidates evaluation (O2).
- Green health with unloaded/wrong weights or failed sources cannot imply readiness (O3).

### Task O1: Retention, deletion and privacy evidence

**Files:** Create `services/api/app/deletion.py`, `services/api/app/observability.py`, `tests/security/test_privacy.py`, `tests/integration/test_deletion_restore.py`, `infra/backup-policy.md`.
**Consumes:** F2 policies, F3 jobs/tombstones, S4 ephemeral graph.
**Produces:** `purge_document(document_id: UUID, tenant_id: UUID) -> PurgeReceipt`; `reapply_tombstones(restore_id: str) -> RestoreAudit`; sanitized technical observability and deletion SLA receipts.

- [ ] Write tests for live link/caches/worker leases after deletion, two-tenant canaries, no automatic age expiry, 24h purge SLA, 30-day backup policy and restored tombstones. Assert doc remains before explicit deletion; all access stops at tombstone; restored copies stay inaccessible.
- [ ] Run `uv run pytest tests/security/test_privacy.py tests/integration/test_deletion_restore.py -q`; expect failure.
- [ ] Implement durable purge/retry/escalation, cache/link invalidation, storage authorization gateway, derivative/vector cleanup, backup expiry and restore barriers. Keep deletion IDs/times beyond the usable backup window; never save private bodies in deletion records.
- [ ] Disable private external tracing, search checkpointing and body logging. Scan controlled canaries across logs/metrics/job/checkpoint/storage paths without writing sensitive evidence into reports.
- [ ] Rehearse actual time-bounded purge and a backup restore; record measured receipts for G16/G17/G18. Unit fake clocks alone cannot certify real backup expiry.
- [ ] Commit: `git add services/api/app/deletion.py services/api/app/observability.py tests/security tests/integration/test_deletion_restore.py infra/backup-policy.md`; `git commit -m "feat: enforce deletion and privacy operations"`.

### Task O2: Professional evaluation, hardware pilot and ranking decision

**Files:** Create `evaluation/cases.jsonl`, `evaluation/thresholds.json`, `evaluation/run.py`, `tests/evaluation/test_metrics.py`, `verification/evidence/quality-report.json`.
**Consumes:** S2/S3/S4 arms, C3 reviewed coverage, R15/R16 strata.
**Produces:** `evaluate(cases_path: Path, thresholds_path: Path) -> EvaluationReport`; immutable reviewed ground truth, workload/threshold freeze and reranking adoption decision.

- [ ] Write metric tests with hand-calculated relevance/rank cases; assert >=200 unique professional reviews, disjoint calibration/holdout IDs, all es/ca/gl/eu and territorial tiers, negatives and historical cases. Reject missing strata, edited post-freeze thresholds or absent reviewer evidence.
- [ ] Run `uv run pytest tests/evaluation/test_metrics.py -q`; expect failure.
- [ ] Have professionals label section/version-level cases and source/provenance errors. Run pilot on actual hardware with corpus sizes, concurrent searches/uploads, warm/cold modes, rates/timeouts and costs.
- [ ] Freeze numeric Recall@20, MRR@10, nDCG@10, Precision@5, p95, error/territorial/temporal and stratum minimum thresholds before holdout. Version/hash cases, thresholds and hardware profile. No universal confidence cutoff substitutes for legal relevance review.
- [ ] Run FTS, hybrid and hybrid+LAYA on holdout; measure confidence/truncation/option-order effects. Record G08/G09/G10/G21. Reject influence that fails approved thresholds; keeping shadow remains a valid adoption outcome.
- [ ] Commit: `git add evaluation tests/evaluation verification/evidence/quality-report.json`; `git commit -m "test: record professionally reviewed search evaluation"`.

### Task O3: Self-host deployment, rehearsal and evidence gate

**Files:** Create `infra/compose.yaml`, `infra/api/Dockerfile`, `infra/ingest/Dockerfile`, `infra/operations.md`, `tests/ops/test_readiness.py`, `verification/evidence/release-review.json`; populate `verification/release-evidence.json`.
**Consumes:** F1 pins, F2 migrations/auth/storage, C3 national audit, O1 purge/restore, O2 evaluation.
**Produces:** reproducible deployment/runbooks, tested rollback/restore and reviewed release evidence manifest.

- [ ] Write readiness cases for wrong checkpoint hash, absent bearer, empty corpus, missing municipality, failed daily source, expired secret and deleted-canary restoration. Assert liveness can remain green while readiness/release is blocked.
- [ ] Run `uv run pytest tests/ops/test_readiness.py -q`; expect failure.
- [ ] Implement private networks, TLS gateway, secrets, pinned images, least-privilege roles, persistent job leases, encrypted backups, alerts, health/readiness and measured resource limits. Do not publish inference directly.
- [ ] Rehearse migrations, backups/restoration, source lag alerts, LAYA failure/rollback and capacity. Collect redacted evidence with paths/SHA256 and named reviewers for every G01..G22 gate.
- [ ] Run all relevant tests, professional release review and `python scripts/verify_package.py --release`. Missing/failed/unreviewed evidence blocks; this planning checker only validates artifact integrity/attestations and cannot replace substantive review.
- [ ] Commit: `git add infra tests/ops verification`; `git commit -m "ops: rehearse verified self hosted release"`. Deployment/publishing occurs only when explicitly authorized in that future task.

