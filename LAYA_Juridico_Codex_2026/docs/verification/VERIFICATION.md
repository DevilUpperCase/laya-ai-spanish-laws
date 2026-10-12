# Verification and release evidence

## Offline commands

Local Markdown links are checked too. Source audit structural checks require reconciled nonnegative integer counts, reviewed ranges, and source-to-jurisdiction mappings matching the official hierarchy.

From the package folder with Python 3.10+ and no additional packages:

```powershell
python scripts/verify_package.py
python -m unittest discover -s tests -v
python scripts/verify_package.py --release
```

The first command validates required files, JSON syntax/contracts, R01..R24 task/gate traceability, Python syntax and unittest results. It writes reports. It never reads .env, installs dependencies, downloads weights, runs migrations, invokes production services or edits application code. Relative paths resolve from the script location, not the shell's working directory.

Exit 0 means the selected check scope passed. Exit 1 means offline checks failed or --release found release blockers. Exit 2 is a CLI usage error. A normal offline pass can coexist with a blocked release; both are shown in the report. Running --release now should return 1: all G01..G22 start not_run.

The original six tests cover fake-router mechanics/RRF and deterministic explanation examples. New verifier tests exercise absent/forged evidence, path escape, tampered hashes and incomplete coverage handling. Neither suite proves the future product works.

## Evidence workflow for future implementation

1. Run the real procedure in ACCEPTANCE_MATRIX.csv and its owning plan task. A skipped test has not passed.
2. Save reviewed, redacted artifacts under verification/evidence/. Keep private contents/secrets out; report IDs/counters only.
3. Add each artifact as {"path":"verification/evidence/report.json","sha256":"<64 hex characters>"} in its release-evidence.json gate. Set status passed only after substantive success; record reviewed_by and reviewed_at as an ISO date/time.
4. G13 additionally reads coverage-inventory.json: approved official inventory artifact, exact entity-set mapping, independent review, verified entity statuses and hashed audited source records. Authority CSV fields are jurisdiction_id,level,parent_id,name,official_source_url; required levels include state/autonomous_community/autonomous_city/province/municipality plus applicable island/foral entries. An approved complete official snapshot and supplemental inventory are required; a tiny invented CSV cannot substantively satisfy the gate.
5. Each referenced source audit uses the source template, verified status, reviewed terms/current/history/reconciliation and original fixture/evidence references with hashes. No missing required current periods. Professional review checks actual index/issue/record completeness independently of this structural checker.
6. G21 assessment records reviewed_query_count >=200, languages es/ca/gl/eu, all territorial tiers, positive temporal/negative counts, and thresholds_frozen_before_holdout=true. The hashed actual reviews/measurements, not booleans alone, are substantive evidence.
7. G16 assessment records immediate_revocation=true, live_purge_max_hours <=24, backup_max_age_days <=30 and retention_mode=until_tenant_deletion. G17 assessment records tombstones_reapplied_before_access=true.
8. Run --release, inspect every blocker and obtain the final professional/engineering review. The checker validates integrity and minimum attestations, **not** reviewer authenticity, actual deployment state, legal completeness or statistical validity.

Any failed/missing/malformed gate, artifact, reviewer, hash, current jurisdiction or semantic minimum keeps release blocked. There is no skip/waiver flag. File hashes protect against later edits; they do not prove an artifact's claims are true.

## Evidence record shapes

A future passed gate requires this shape, with real reviewed artifacts; the markers below are documentation and cannot pass validation:

```json
{
  "status": "passed",
  "reviewed_by": "<real reviewer identifier>",
  "reviewed_at": "<ISO review timestamp>",
  "evidence": [
    {"path": "verification/evidence/<real report filename>", "sha256": "<actual SHA256>"}
  ],
  "assessment": {}
}
```

Each entry in coverage-inventory.json `entities` requires `jurisdiction_id`, `level`, `parent_id`, `current_normative_status: "verified"`, `reviewed_by`, `reviewed_at`, and `source_audits` (a nonempty list of hashed artifact references). Its ID/level/parent must match the authoritative CSV. Each source audit must include the entity ID in `territory_ids`.

Source audit `fixtures` and `reconciliation.evidence` are lists of the same path/SHA256 references. `current_range.start/end` and available-history bounds are ISO dates. An absent historical range requires nonempty reviewed `unavailable_ranges` records describing why history is unavailable. Reconciliation counts are nonnegative integers with `expected_publications == integrated_publications` and no missing required periods. These are reviewed assertions backed by the actual reconciliation reports, not completeness inferred by the verifier.

G21 assessment fields: `reviewed_query_count`, `languages`, `territorial_tiers`, `temporal_cases`, `negative_cases`, and `thresholds_frozen_before_holdout`. G16 fields: `retention_mode`, `immediate_revocation`, `live_purge_max_hours`, `backup_max_age_days`. G17 field: `tombstones_reapplied_before_access`. All other gates still require substantive artifacts/review even without specialized assessment fields.

Keep all real evidence redacted. Professional reviews, official geographic snapshots, publication reconciliation and measured thresholds must remain independently inspectable; do not replace them with the synthetic test fixtures in tests/test_verification.py.

## Baseline not executed

FastAPI/live workflow, dependency/model compatibility, real LAYA inference, auth/RLS/storage, original-source ingestion, national coverage/history audit, multilingual professional evaluation, OCR/upload UI, latency/load, backup/deletion/restore, licenses and deployment are not executed by this planning task. Their missing evidence remains explicit in reports.

## Environment and dependency templates

.env.example defines proposed configuration only. dependency-pins.template.json and evaluation-policy.template.json deliberately have unset values. F1/O2 must replace them with compatible measured pins/thresholds before relevant release gates. Do not interpret an unset model revision, health success or disabled reranking as completion of mandatory LAYA integration.
