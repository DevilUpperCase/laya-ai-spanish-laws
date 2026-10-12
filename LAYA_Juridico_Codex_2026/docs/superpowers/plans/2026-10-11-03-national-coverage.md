# National Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce reviewed source coverage for every required Spanish jurisdiction before first release.

**Architecture:** A dated official entity inventory maps to audited publishers and source-specific adapters. Reconciliation proves current and available-history coverage; missing entities remain release blockers.

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

- Municipal mergers/name changes invalidate stale code/name joins (C1).
- One bulletin may cover many entities; one entity may require several publishers (C1/C2).
- A single imported norm is not complete jurisdiction coverage; zero-publication periods need evidence (C3).
- Regional/island/foral regulations and municipal ordinances must not be omitted (C1/C2).
- Source access/format changes, skipped pages and stale cursors cannot silently pass completeness (C2/C3).

### Task C1: Official inventory, source audit and coverage mapping

**Files:** Create `services/ingest/ingest/inventory.py`, `services/ingest/ingest/source_registry.py`, `tests/ingest/test_inventory.py`, `verification/coverage-inventory.json` (populate existing template), `verification/evidence/jurisdictions.csv`.
**Consumes:** S1 source contracts; sources templates; current official INE/administrative directories and supplemental island/foral inventories.
**Produces:** `load_jurisdictions(snapshot_path: Path) -> list[Jurisdiction]`; `audit_source(manifest: dict) -> SourceAudit`; `map_coverage(entities, audits) -> CoverageReport`.

- [ ] Write tests for exact authoritative ID-set equality, duplicate IDs, stale codes, parent mismatch, missing municipality, missing source, unapproved terms and unknown capability. Assert any omission blocks release even when all discovered entries are marked verified.
- [ ] Run `uv run pytest tests/ingest/test_inventory.py -q`; expect failure.
- [ ] Fetch dated official snapshots lawfully, store URL/hash/date and reviewed geographic hierarchy; add relevant island/foral publishers. Do not convert the 43-link directory into a complete province/municipality inventory.
- [ ] Audit every required source against sources/README.md. Record each adapter's exact paths, supported methods, original fixture hashes, terms, normative scope, historical limits and reconciliation strategy. Unavailable current source/entity is blocked, not silently exempted.
- [ ] Have professional/source reviewers approve inventory and mappings; run tests and save G13/G14 evidence. Pin the snapshot used for launch and detect later changes.
- [ ] Commit: `git add services/ingest/ingest/inventory.py services/ingest/ingest/source_registry.py tests/ingest/test_inventory.py verification/coverage-inventory.json verification/evidence/jurisdictions.csv sources`; `git commit -m "feat: inventory national normative coverage"`.

### Task C2: Audited connector portfolio

**Files:** Create `services/ingest/ingest/dogc.py`, `services/ingest/ingest/adapters.py`, `services/ingest/ingest/parsers.py`, `tests/ingest/test_source_contract.py`, `docs/source-implementation-index.md`.
**Consumes:** S1 SourceAdapter; C1 reviewed registry and exact source fixture/adapter paths.
**Produces:** `get_adapter(source_id: str) -> SourceAdapter`; `parse_publication(source_id: str, raw: RawPublication) -> ParsedPublication`; versioned source-specific adapter implementation index.

- [ ] Create a parameterized contract case for **every** required audited source: full discovery pages, normative-vs-announcement classification, version/amendment records, language/territory mapping, permitted missing-history limits and retry/idempotency. Assert registry source set equals tested source set.
- [ ] Run `uv run pytest tests/ingest/test_source_contract.py -q`; expect failure for unimplemented sources.
- [ ] Implement DOGC after verifying actual export schema/pagination/terms. For remaining regional/provincial/municipal/island/foral sources, generate one bounded implementation entry per C1 source ID with exact code/fixture/test paths and verified transport/parser rules before writing that source's code. The index is mandatory evidence; generic unchecked scraping cannot satisfy a source entry.
- [ ] Reuse parser mechanics only when each source has its own verified configuration, original fixtures, limits, versioning rules and contract tests. Use official feeds/bulk/API where permitted; audit site-specific retrieval if none exists.
- [ ] Run every source's fixtures plus controlled allowed live reconciliation. Record G14 evidence and C3 inputs; a disconnected municipality is still blocked even if all other sources pass.
- [ ] Commit each source separately with its manifest, fixtures, tests and index entry; commit message `feat: add audited <source_id> ingestion`.

### Task C3: Daily reconciliation and national release coverage

**Files:** Create `services/ingest/ingest/reconcile.py`, `services/ingest/ingest/scheduler.py`, `services/api/app/coverage.py`, `tests/ingest/test_reconciliation.py`, `verification/evidence/national-coverage.json`.
**Consumes:** C1 inventory and mappings, C2 adapters, S1 transactional ingestion.
**Produces:** `reconcile_all(start_date: date, end_date: date) -> CoverageReport`; `CoverageService.report() -> CoverageReport`; source-run/gap and coverage attestations.

- [ ] Write tests for skipped page/day, network error mid-window, replay, zero-publication day with official evidence, missing current jurisdiction, stale cursor and available-history omission. Assert freshness never advances past partial failure and source count alone cannot pass a jurisdiction.
- [ ] Run `uv run pytest tests/ingest/test_reconciliation.py -q`; expect failure.
- [ ] Implement daily T-7..T windows, weekly failed-period recovery, monthly historical backfills, transactional cursor publication, expected-issue/count reconciliation and monitored lag. Track source check time separately from last integrated publication.
- [ ] Populate every entity's source mappings and audit hashes; prove all available approved history within documented ranges. For true unavailable history retain professional review and visible limitations; missing current coverage cannot be waived.
- [ ] Run nationwide reconciliation and independent coverage review. G13/G14/G15 must pass before any first release claim. Baseline shipped flags or directory completeness are insufficient.
- [ ] Commit: `git add services/ingest/ingest/reconcile.py services/ingest/ingest/scheduler.py services/api/app/coverage.py tests/ingest/test_reconciliation.py verification/evidence`; `git commit -m "feat: reconcile verified national coverage"`.

