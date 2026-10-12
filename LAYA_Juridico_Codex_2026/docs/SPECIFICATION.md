# Confirmed product specification

Owner confirmation: 2026-10-11. Initial deliverable: English plans, contracts, templates, offline verifier and an honest baseline report. On 2026-10-12 the owner additionally authorized application implementation, database population, and starting Docker Desktop for a separate local development database. Public/production deployment remains separate work. The requirements below remain binding; internal development progress does not establish first-release readiness.

## Global constraints

- Mandatory tools: FastAPI, LangChain Core, LangGraph, and local LAYA.
- No generative LLMs, external inference, private external tracing, or persisted private search graph state.
- Self-host Supabase/PostgreSQL, authentication, private storage, BGE-M3, and LAYA.
- Next.js + TypeScript + Tailwind + shadcn/ui; Spanish UI initially.
- Search/evaluation languages: es, ca, gl, eu.
- First release requires verified coverage for every required Spanish jurisdiction; internal milestones are not releases.
- Retain documents until tenant deletion; revoke access immediately, remove live copies within 24 hours, expire encrypted backups within 30 days, and reapply deletion records on restoration.
- Professional evaluation requires at least 200 queries; performance thresholds are frozen after a hardware pilot before launch evaluation.

## Requirements

| ID | Requirement | Observable acceptance |
|---|---|---|
| R01 | All four tools are real runtime components. | Tests exercise FastAPI routes, LangChain interfaces, a compiled LangGraph and private LAYA with real weights. |
| R02 | Non-generative local processing. | Dependency/runtime egress audit finds no generative/provider path; OCR/explanations are local/deterministic. |
| R03 | Self-hosted data and inference. | Deployment inventory, network tests and restore rehearsal prove selected hosting. |
| R04 | Question and PDF/DOCX selection search. | Real upload/extraction, page/offset selection, progress/errors and related search work end to end. |
| R05 | Isolation in every data path. | Two-tenant API/SQL/storage/cache/worker tests find zero leaks, including multi-membership users. |
| R06 | Evidence-backed results. | Every result has official provenance, literal extract, section/version, territory, warnings and deterministic span-backed reasons. |
| R07 | Correct legal timelines. | Publication/effective/ingestion dates remain distinct; unknown effective dates stay unknown in historical queries. |
| R08 | All-jurisdiction first release. | Every entity in an independently reviewed official inventory maps to verified normative coverage; missing required entities/periods block release. |
| R09 | Bounded history. | Current legislation and all history available from approved sources are ingested; unavailable history is documented and reviewed. |
| R10 | Audited ingestion. | Adapters preserve originals/hash/provenance, reconcile issues/pagination, classify normative acts and have reviewed reuse terms/fixtures. |
| R11 | Daily synchronization. | Transactional publication, cursor/watermark, T-7..T reconciliation, visible gaps and lag/failure alerts exist. Failed runs never say fully up to date. |
| R12 | Hybrid recall/grouping. | Exact refs, FTS/trigram, local 1024-d BGE-M3 and RRF are evaluated with territorial/temporal filtering and diversity. |
| R13 | Mandatory LAYA shadow adoption. | Nonempty candidate sets invoke local LAYA; shadow data is text-free; production ranking influence needs separate approval. |
| R14 | Degraded search. | Timeout/overload/circuit/malformed/truncated decisions return baseline results and warnings without losing candidates. |
| R15 | Language support. | es/ca/gl/eu have reviewed cases and metrics; normalization preserves original spans. |
| R16 | Professional evaluation. | At least 200 reviewed cases cover tiers, languages, temporal cases and negatives; ground truth identifies section versions. |
| R17 | Measured performance/adoption. | Frozen pilot hardware/workload/thresholds precede holdout; FTS/hybrid/hybrid+LAYA report quality, p50/p95 and errors. |
| R18 | Retention/deletion. | No automatic 30-day expiry; deletion hides every access path immediately, purges live copies within 24h and backups within 30 days. |
| R19 | Restore respects deletions. | Tombstones are reapplied before access; no deleted content resurrects. |
| R20 | Workflow/log privacy. | Canary content/query/secrets are absent from logs/APM/metrics/checkpoints; no private persistent search state or external tracing. |
| R21 | Reproducibility/terms. | Locks, image digests, model revisions/file hashes, embedding dimensions and code/model/source terms are verified. |
| R22 | Accessible functional UI. | Search/document/coverage views, real actions, warnings, mobile/keyboard checks and WCAG 2.2 AA review exist. |
| R23 | Operable reversible deployment. | Private networks/secrets/roles/queues, migrations, backups, alerts, capacity and LAYA rollback are rehearsed. |
| R24 | Honest verification. | Status, command/procedure, evidence and limits exist for every check; mocks cannot pass real deployment gates. |

## Coverage meaning

Import a dated official inventory of the state, every autonomous community/city, province and municipality, supplemented by relevant island/foral institutions. Do not hard-code a municipal count. Jurisdictions and publishers are separate: one bulletin serves many entities and an entity can need several sources.

Include laws, regulations and ordinances; exclude individual administrative announcements. One law per municipality is not proof of complete available normative coverage. A legitimate zero-publication period needs reconciliation evidence rather than an unexplained gap.

Every source needs approved access/reuse terms, audited date ranges, expected issues/publications, missing intervals and reconciliation. Unavailable historical archives can be reviewed limitations under R09; they cannot excuse missing current coverage under R08. If current coverage cannot be verified, release remains blocked while internal development may proceed.

## Evaluation boundaries

The 200-case minimum is a floor, not proof of statistical sufficiency or nationwide completeness. Professional reviewers approve language/territory strata and source completeness separately. Freeze immutable labels and calibration/holdout splits.

The pilot records devices, corpus/document sizes, concurrent users, query/upload rates, warm/cold state, timeouts, quality and latency. Freeze numeric thresholds and stratum minima before holdout release evaluation. No latency guarantee is invented in this package.

LAYA stays in shadow until comparison approval. Truncated/malformed decisions cannot influence ordering. Retrieval owns recall; official metadata owns validity. An outage permits warned baseline search, but missing real deployment/model evidence blocks first release.

The verifier checks local structure, tests, evidence paths/hashes and selected attestations. It cannot authenticate a professional reviewer or prove that external inventory/corpus claims are true. Real reviewed evidence is mandatory.

The acceptance matrix maps requirements to tasks and gates. The confirmed specification supersedes conflicting legacy recommendations.
