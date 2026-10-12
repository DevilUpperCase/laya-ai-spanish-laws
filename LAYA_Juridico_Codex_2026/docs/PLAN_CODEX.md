# Implementation roadmap — confirmed 2026-10-11

The current delivery is plans and verification files only. Implement the product later, in a repository separate from upstream LAYA, using only the requested task.

## Execution order and task map

| Plan | Tasks | Prerequisites | Internal outcome |
|---|---|---|---|
| [01 Foundation](superpowers/plans/2026-10-11-01-foundation.md) | F1 runtime/types; F2 auth/DB/storage; F3 documents; F4 UI | Confirmed spec | Authorized API/document foundations; F4 real-data validation waits for S4. |
| [02 Evidence search](superpowers/plans/2026-10-11-02-search.md) | S1 BOE; S2 retrieval; S3 LAYA; S4 graph/explanations | F1/F2; F3 for selection | Search and documents on internal corpus, mandatory local LAYA shadow stage. |
| [03 National coverage](superpowers/plans/2026-10-11-03-national-coverage.md) | C1 inventory/audits; C2 adapters; C3 reconciliation | S1 source contract; F2 DB | Reviewed every-jurisdiction current/available-history coverage. |
| [04 Release operations](superpowers/plans/2026-10-11-04-release-operations.md) | O1 deletion/privacy; O2 evaluation; O3 deployment/review | O1 after F3; O2 after S4; O3 after all | Measured release decision and self-host runbooks. |

C1 source audits may proceed once source contracts exist; F4 UI fixtures must stay labeled DEMO until real APIs work. No internal milestone is the first release. The first release requires **every** coverage and operational gate; there is no BOE-only launch exception.

Each plan includes exact interfaces, file paths, test intent, failure-first checks, verification commands and future commit checkpoints. C1 locks audited source IDs; C2 records concrete paths and cases for every additional source before implementing it, since unknown source capabilities cannot be honestly specified today.

## Required acceptance

See [specification](SPECIFICATION.md), [file map](FILE_MAP.md), [matrix](verification/ACCEPTANCE_MATRIX.csv) and [verification guide](verification/VERIFICATION.md). G01..G22 are product gates; all begin not_run. Package success never implies application readiness.

## Plan self-review

- R01..R24 each map to at least one gate and implementation task.
- Types/signatures match ARCHITECTURE and API/DATA contracts; shared types originate in F1 and source types in S1.
- Each Review Focus item has a test in its owner task.
- Model pins, source capability audits and numerical thresholds are explicit measured deliverables with blocking gates; none are invented as completed facts.
- Source inventory completeness is reviewed separately from sampled search quality.
- No app/deployment work is authorized by delivery of these plans.
