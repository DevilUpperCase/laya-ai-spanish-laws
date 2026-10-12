# Source audit and jurisdiction coverage

This package contains **templates**, not verified source records or a national coverage claim.

1. C1 imports official dated geographic inventories, supplements required island/foral institutions, stores raw inventory evidence and produces `verification/evidence/jurisdictions.csv` with `jurisdiction_id,level,parent_id,name,official_source_url`.
2. Copy source-audit.template.json into a concrete source record only after checking that publisher's actual discovery, history, formats, limits and terms. Resolve source ID and all code/fixture paths in C1/C2; no placeholder may be verified.
3. Keep original permitted fixtures, hashes and endpoint/format observations. Link terms approval, current-range audit, available-history reconciliation, exceptions and independent reviewer evidence.
4. Map every authoritative entity to all required publishers via jurisdiction-coverage.template.csv. Several sources may be necessary; a provincial bulletin can cover many municipalities but classification/mapping needs evidence.
5. Populate verification/coverage-inventory.json with exact authoritative ID-set equality and per-entity reviewed source/audit artifacts. Reconcile every required source/current range and all available history; missing/unverified current coverage blocks first release.

## Evidence checklist per source

- Official publisher/URLs/territory and dated inventory revision.
- Access method and actual supported content types; no assumed API just because a link exists.
- Approved code/model/source reuse terms, attribution and informational-consolidation notices.
- Allowed cadence/rate and backoff; original fixtures with bytes/SHA256 and fetch dates.
- Audited current/historical intervals; available vs unavailable history with review.
- Complete discovery/pagination/index/issue counts; zero-publication periods evidenced, missing pages/days tracked.
- Normative-vs-announcement classification, amendments/versions and original/effective date semantics.
- Stable cursor/idempotency; transactional successful publication; daily T-7..T and recovery.
- Separate source check/successful sync/latest integrated publication; alerting and parser-change tests.
- Every mapped geographic entity checked; one imported norm is insufficient completeness evidence.

The BOE directory is an inventory starting point, not proof of complete geography or available legislation. Keep unknown/partial status until real reconciliation and professional review. A legitimate unavailable historical range is documented under R09; unavailable current jurisdiction coverage remains a blocker under R08.
