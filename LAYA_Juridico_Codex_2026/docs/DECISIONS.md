# Decisions and evidence

Owner confirmed 2026-10-11 through grill-me/grilling interview.

| Decision | Confirmed value | Effect |
|---|---|---|
| Deliverable | Plan and verification files only. | No app implementation/deployment now. |
| Stack | FastAPI, LangChain Core, LangGraph, local LAYA. | Every component must execute a real role. |
| Generation | None. | Local embeddings/OCR, fixed labels, deterministic explanations. |
| Hosting | Self-host database/storage/inference. | Managed Supabase is not selected. |
| Launch | Every jurisdiction verified. | Internal BOE/regional milestones cannot release. |
| History | Current + officially available history. | Audited ranges and reviewed unavailable-history limits. |
| LAYA | Shadow first, warned outage fallback. | Production ordering needs a separate comparison gate. |
| Review | Measured checks + professional review. | >=200 cases, provenance and zero isolation leaks. |
| Retention | Until tenant deletion. | No automatic 30-day document expiry. |
| Final details | es/ca/gl/eu; Spanish UI; immediate revocation, 24h live purge, 30-day backup expiry, restore tombstones. | Explicitly accepted in final confirmation. |
| Performance | Pilot then freeze thresholds. | No invented guarantee; holdout uses immutable thresholds. |

## Observed findings

Initial artifacts: HTML prototype, SQL draft, three example modules, six unit tests. Original tests passed using a fake router; they cannot prove real weights, quality, auth, storage, ingestion or deployment. The inspected workspace root is not a Git repository. Upstream was not modified.

The example in-process adapter agrees with Router.predict_batch request order and shape. Its defaults for missing metadata and unpinned smoke router require replacement during implementation. [Router source](https://github.com/NandhaKishorM/laya/blob/main/laya/router.py).

The upstream main branch inspected advertises 0.4.3 and serving/integration extras; that observation is not a tested dependency pin. Verify an immutable compatible release in F1. [Package metadata](https://github.com/NandhaKishorM/laya/blob/main/pyproject.toml).

The official directory enumerates 17 communities, Ceuta/Melilla and 43 provincial links. It does not certify APIs, completeness, or the absence of unlisted bulletins. [BOE directory](https://www.boe.es/legislacion/otros_diarios_oficiales.php).

BOE database scope cannot establish provincial/municipal completeness. Consolidations are informational and incorporate express changes; historical/format limits require their own audit. Nationwide coverage must therefore be evidenced independently. [Database help](https://www.boe.es/buscar/ayudas/legislacion_ayuda.php), [consolidation help](https://www.boe.es/buscar/ayudas/legislacion_actualizada.php?lang=es).

## Primary references for implementation audits

- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/).
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) and [persistence](https://docs.langchain.com/oss/python/langgraph/persistence).
- [LAYA HTTP API](https://github.com/NandhaKishorM/laya/blob/main/docs/http-api.md) and [integration guide](https://github.com/NandhaKishorM/laya/blob/main/docs/langchain.md). Recheck against the selected release; integration prose has batching ambiguities.
- [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).
- [BOE API](https://www.boe.es/datosabiertos/api/api.php), [reuse terms](https://www.boe.es/informacion/aviso_legal/), [INE municipality inventory](https://www.ine.es/daco/daco42/codmun/codmun00i.htm), [DOGC catalogue](https://datos.gob.es/es/catalogo/a09002970-normativa-de-cataluna-publicada-en-el-dogc), [BGE-M3 card](https://huggingface.co/BAAI/bge-m3).

Links are audit references, not proof that package compatibility, licenses, exports, geographic codes, latency, or relevance have been validated in this task.


## Completion decisions ? 2026-10-12

- Self-hosted Supabase Auth verifies passwords in its isolated database. The browser receives a random opaque HttpOnly cookie whose digest/expiry are stored in the application database; RS256 bearer authentication remains for automation. Membership is always resolved live.
- Use a fixed same-origin streaming Next.js gateway to preserve cookie boundaries; browser JWT/manual tenant sign-in was removed.
- Register limited current-user Windows tasks for logon supervision and 03:00 encrypted backup, without public listeners or persistent plaintext logs.
- Exact BOE recovery evidence resolves all earlier 45 failures; it does not close national coverage. Publisher imports/finite manifests retain normative/history/annex limits explicitly.
- Current-version lookup uses an atomic dated cache only when compatible with request semantics. Explicit historical/effectiveness filters preserve qualifying SQL; custom plans avoid large-corpus generic-plan regressions.
- Authenticated streaming backups plus current independent deletion replay were rehearsed for private schemas and a synthetic canary. Off-host replication, separate keys, full recovery and elapsed expiry remain external production evidence.
- 200 multilingual cases are drafts. The measured hardware pilot does not freeze quality/performance thresholds. No reviewer identity, professional judgments, deployment domain or licensing approval is invented.
