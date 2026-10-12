# Execution ledger — docs/superpowers/plans/2026-10-12-document-research.md

Owner confirmed implementation on 2026-10-12. Spec: docs/specs/2026-10-12-document-research.md. All five tasks are pending. No national, professional quality or training approval inferred.

Ruling: use the existing authorized workspace and this durable ledger; no Git repository or installed superpowers TDD/workspace helper exists. Use failure-first pytest directly and retain the ledger rather than deleting it. Cost: no Git rollback checkpoint; preserve existing migrations and reversible configuration.

Pre-flight: Tasks 1/4 share library/note routes; Task 1 supplies recoverable trash while existing DELETE stays permanent. Tasks 2/5 share publication assets. Tasks 3/5 share explicit search scopes; unknown classifications appear only in all-publication search. Tasks 1/3 share document lifecycle and private index cleanup. No contradictory interfaces found.

Task 1: initial missing-module RED; two real PostgreSQL library/revision/trash/restore/permanent-deletion/notes-purge tests GREEN (5.76s). Additive migration 013 applied; original files survive trash and deleted linked notes are purged. Existing permanent DELETE remains compatible. Broader recovery/browser checks remain pending.

Ruling: add a worker-only scoped lease function for deterministic canary tests/recovery; global leases could consume older private-index jobs instead of the test extraction. Cost: one additive migration/API-internal optional argument; user API gains no elevated worker access. Initial reader test failed because its synthetic bearer omitted required iat, corrected without changing authentication.
Task 2 original source boundary RED?GREEN; actual Constitution PDF captured. Task 3 query-plan/graph suite 15 passed. Task 5 real summary/checker RED?GREEN, bounded BOE 2/160 and BORME 2/54 captured; partial remains explicit.
Windows text-encoding issue corrected; use explicit UTF-8 on every subsequent file read/write. Compile/typecheck passed after removing a legacy decoded BOM.

Backend checkpoint: migrations 013?018 applied; 8 real database attachment/library/reader/PDF+OCR extraction tests passed in 35.65s. Extraction regression RED?GREEN after granting tenant-bound job INSERT to worker. BOE/BORME real summary tests and dimension checker passed. Next production build passed before final context-annotation changes; a final build/browser verification is pending.
Implemented public version/asset readers, private LangChain retrieval and private LangGraph, bounded durable private index batches, intent and engine/context explanations, new library/notebook/trash/attachment UI. Real source import is bounded/partial; expanded all-publication audits remain absent. Full original hash verification is running. Remaining: final corpus/daily integration, UI actions/references/role details, comparison and source-check regressions, scoped restore rehearsal, full suite/browser/docs and one independent review.
Approval review temporarily failed on a usage limit; user instructed continue and the same escalated action subsequently succeeded. No bypass was used.

Query-context correction: only passages actually added to the bounded retrieval plan are serialized as used context. Per-result engine signals carry the context document/page/offsets; selected-context diversity covers distinct files first. Private search now executes its own non-persistent LangGraph. Training-readiness remains blocked because no professional candidate labels exist.
