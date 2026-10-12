# File map

See [CODE_REFERENCE.md](CODE_REFERENCE.md) for the generated complete owned-code inventory and [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for current module responsibilities. This original planning map is retained for traceability.

Paths are relative to this folder. The original present/planned tables preserve the design map. The actual implementation added on 2026-10-12 is listed below; future production features remain plans.

## Implemented development files

| Path | Responsibility |
|---|---|
| services/api/app | FastAPI/auth, active-tenant database access, body limits, uploads/selection/download/deletion, durable worker, actual LangChain retrieval/LangGraph search, local model clients and coverage warnings. |
| services/ingest/ingest | BOE XML discovery/parsing, version/provenance/chunk storage, official INE inventory and publisher-directory registry. |
| db/migrations/001_legal.sql through 007_title_trigram.sql | Checksum-tracked legal/private schemas, restricted roles, composite tenant keys, RLS, worker purge, vector and retrieval indexes. |
| apps/web | Built Next.js/TypeScript/Tailwind Spanish search, documents and coverage screens; npm package lock. |
| scripts/setup_docker.py, migrate.py, create_local_session.py | Separate local DB/bootstrap, restricted roles and development-only short-lived RSA session. |
| scripts/capture_sources.py, populate_database.py, sync_boe.py, embed_corpus.py | Real official source capture, resumable ingestion/update reconciliation and local vector indexing. |
| scripts/download_models.py, serve_laya.py, run_api.py | Immutable local model artifacts and local servers. |
| scripts/reapply_deletions.py; infra/backup-policy.md | Independent deletion-journal restore barrier and outstanding production obligations. |
| evaluation | Ranking metrics and reviewed holdout/frozen-threshold validation; professional data not fabricated. |
| docs/contracts/openapi.json; verification/dependency-pins.json | Generated actual route schemas and observed locked dependencies/model metadata. |
| tests/integration, ingest, search, security, evaluation, e2e | Real database/model checks, regression checks and browser flow using synthetic private documents. |
| verification/reports | Actual population/runtime/browser/test reports; offline release evidence remains blocked. |
| docs/LOCAL_OPERATIONS.md | Local commands, operational boundaries and pending release requirements. |

## Present planning package

| Files | Responsibility |
|---|---|
| AGENTS.md, README.md | Current scope, authority, entrypoints and honest status. |
| docs/SPECIFICATION.md, ARCHITECTURE.md, DECISIONS.md | Requirements, boundaries and confirmed choices/evidence. |
| docs/PLAN_CODEX.md; docs/superpowers/plans/2026-10-11-01-foundation.md through -04-release-operations.md | Roadmap and four executable implementation plans. |
| docs/contracts/API.md, api-contract.json, DATA.md | Planned API interface and entity/security constraints. |
| docs/verification/VERIFICATION.md, ACCEPTANCE_MATRIX.csv | Commands, evidence workflow and traceable product gates. |
| sources/README.md, source-audit.template.json, jurisdiction-coverage.template.csv | Source audit/mapping templates; no sources falsely verified. |
| verification/package-manifest.json | Required files, mandatory tools, R01..R24 and task-to-plan mapping. |
| verification/release-evidence.json, coverage-inventory.json, dependency-pins.template.json, evaluation-policy.template.json | Unexecuted product evidence and measurement templates. |
| scripts/verify_package.py; tests/test_verification.py | Offline verifier and meaningful failure-closed checks. |
| verification/reports/latest.json, latest.md | Generated observed result/limitations. |
| .env.example, .gitignore | Planned configuration and local data exclusion rules. |

## Planned application responsibilities

| Owner | Files | Responsibility |
|---|---|---|
| F1 | pyproject.toml, uv.lock; services/api/app/{contracts,config,main}.py; tests/integration/test_runtime.py; verification/dependency-pins.json | Locked runtime, types, API lifecycle/readiness. |
| F2 | services/api/app/{auth,database}.py; db/migrations/{001_legal,002_private,003_storage}.sql; db/rollback.md; tests/integration/test_isolation.py | Verified identity, active-tenant transactions, DB/storage policies and migration recovery. |
| F3 | services/api/app/{documents,jobs,selection}.py; tests/integration/test_documents.py; tests/fixtures/private/README.md | Quarantine/local extraction, durable jobs, authorized selections/tombstones. |
| F4 | apps/web/package.json; pnpm-lock.yaml; apps/web/src/app/{page.tsx,documents/[id]/page.tsx,coverage/page.tsx}; apps/web/src/lib/api.ts; tests/e2e/search-document.spec.ts | Spanish search/document/coverage UI and browser checks. |
| S1 | services/ingest/ingest/{contracts,boe,pipeline}.py; tests/ingest/test_boe.py; tests/fixtures/boe/README.md | Source types, BOE originals, idempotent parsed version storage. |
| S2 | services/api/app/{retrieval,embeddings,fusion}.py; tests/search/test_retrieval.py; db/migrations/004_retrieval.sql | LangChain retrieval, local vectors, filter-safe fusion. |
| S3 | services/api/app/{laya_client,laya_policy}.py; tests/search/test_laya_transport.py; tests/integration/test_laya_real.py; infra/laya/Dockerfile | Real private LAYA, decision validation/degradation. |
| S4 | services/api/app/{search_graph,search,explanations}.py; tests/search/{test_graph,test_evidence}.py; docs/contracts/openapi.json | Actual compiled graph, evidence routes/reasons and real exported OpenAPI. |
| C1 | services/ingest/ingest/{inventory,source_registry}.py; tests/ingest/test_inventory.py; verification/evidence/jurisdictions.csv | Authoritative geography, sources and reviewed mappings. |
| C2 | services/ingest/ingest/{dogc,adapters,parsers}.py; tests/ingest/test_source_contract.py; docs/source-implementation-index.md | Audited connector portfolio and per-source exact implementation paths. |
| C3 | services/ingest/ingest/{reconcile,scheduler}.py; services/api/app/coverage.py; tests/ingest/test_reconciliation.py; verification/evidence/national-coverage.json | Daily/history reconciliation, visibility and audit report. |
| O1 | services/api/app/{deletion,observability}.py; tests/security/test_privacy.py; tests/integration/test_deletion_restore.py; infra/backup-policy.md | Purge, backup expiry, restore barriers and log/state privacy. |
| O2 | evaluation/{cases.jsonl,thresholds.json,run.py}; tests/evaluation/test_metrics.py; verification/evidence/quality-report.json | Professional ground truth, pilot/frozen thresholds and holdout metrics. |
| O3 | infra/compose.yaml; infra/{api,ingest}/Dockerfile; infra/operations.md; tests/ops/test_readiness.py; verification/evidence/release-review.json | Self-host deployment, rehearsals and final evidence. |

Package __init__.py files and tool configuration belong to their owning task. F1 chooses/install-tests compatible pinned versions; these plans do not invent a working lock. C2 adapter paths are finalized in C1's audited source registry before per-source implementation. Source capabilities cannot be assumed from source names.

## Preserved references

db/001_base.sql; design/buscador-prototipo.html; examples/{laya_adapter,laya_smoke,explanation_rules}.py; tests/{test_adapter,test_explanations}.py; docs/{ARQUITECTURA,FUENTES_Y_COBERTURA,CONTRATO_UX}.md. They remain reference artifacts and do not override the confirmed spec.
