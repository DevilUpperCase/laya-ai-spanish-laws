# Instructions for LAYA Juridico

Use English in conversations and new documentation unless explicitly requested otherwise. Product UI starts in Spanish.

## Authority and current scope

Read docs/SPECIFICATION.md, docs/ARCHITECTURE.md, docs/DECISIONS.md, docs/FILE_MAP.md, and docs/PLAN_CODEX.md first. The English specification records the owner's confirmed decisions of 2026-10-11 and supersedes conflicting recommendations in the original Spanish references.

The owner authorized application implementation and database population on 2026-10-12. Execute the approved implementation plans, keep an honest implementation ledger, and preserve all national release gates. Local development setup is authorized; public deployment and release remain separate. The product is separate from NandhaKishorM/laya; never modify upstream to add our UI/database.

## Mandatory architecture

1. FastAPI in services/api; LangChain Core runnable/retriever interfaces; LangGraph workflows; private local LAYA via laya[serve]; local BGE-M3 embeddings. All four named tools must execute real roles.
2. No generative LLMs anywhere, including OCR, explanations, summaries, or query rewriting. No external inference, private tracing, or persisted private search graph state.
3. Next.js + TypeScript + Tailwind + shadcn/ui in apps/web. Self-host Supabase/PostgreSQL, pgvector, auth, and private storage.
4. Exact references + FTS + embeddings + RRF own recall. LAYA is mandatory, initially invoked in shadow mode. Ranking influence requires evaluation approval. Outages return baseline results with a warning; LAYA cannot infer validity.
5. Public legal and private client chunks stay separate. Enforce membership and active-tenant boundaries in API, RLS, storage, workers, caches. Client tenant IDs are never authority. No elevated role in browser or user search.

## Evidence and release rules

- First release requires audited normative coverage for every state/regional/provincial/municipal jurisdiction, including relevant island/foral sources. Internal milestones are not releases. Unknown/missing required coverage blocks release.
- Include laws, regulations, ordinances, and officially available history; exclude individual administrative announcements. Record unavailable history explicitly; directory entries are not verified ingestion.
- Instrument, original publication, section, version, relationship, source and ingestion run are independent entities. Publication dates are not effective dates. Unknown validity remains unknown with a warning.
- Never fabricate official URLs, titles, dates, articles, citations, or demo results in real search. Explanations require literal spans or verified metadata. Consolidated texts need appropriate informational notices.
- Each source needs audited capabilities/reuse terms/limits, cursor, original fixtures, reconciliation, tests, monitoring, and geographic mappings. Generic scrapers cannot establish completeness.
- At least 200 professionally reviewed cases span territorial tiers, es/ca/gl/eu, temporal cases and negatives. Freeze numeric performance/quality thresholds after a hardware pilot before holdout evaluation.
- Retain documents until tenant deletion. Revoke access immediately, remove live originals/text/vectors within 24h, expire encrypted backups within 30 days, and reapply deletion records before restored access. No private text/query logs.
- Pin dependencies and checkpoint revisions after compatibility checks. Fake-router passes and process health cannot prove inference readiness.

## Delivery

Run python scripts/verify_package.py for offline checks. The --release mode must fail until real product evidence exists. Never mark an unexecuted gate passed.

Future implementation tasks deliver code, meaningful tests, reversible migrations/recovery instructions, usage docs, and UI captures when relevant. State checks not run and why. Preserve existing examples/SQL as references until their replacement task.

Owner confirmed docs/specs/2026-10-12-document-research.md and its implementation plan. Recoverable Papelera precedes permanent deletion; the 24h/30-day deletion rules start only on permanent deletion. No generative LLM remains binding.
