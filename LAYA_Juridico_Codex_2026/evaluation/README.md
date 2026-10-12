# Professional evaluation

There are no invented professional labels or approved performance thresholds.
The release checker remains blocked. `metrics.py` computes Recall@20, MRR@10,
nDCG@10, Precision@5 and negative-case false positives; tests use hand-calculated
synthetic rankings only. Separate provenance/date review and latency/error
evaluation are mandatory.

Supply at least 200 unique cases with `id`, `language`, `tier`, `split`,
`judgments` mapping section-version IDs to grades 0..3, `negative`, `temporal`,
named `reviewer`, and the SHA256 of actual professional review evidence.
Both calibration and holdout are required; holdout must cover es/ca/gl/eu,
state/regional/provincial/municipal/island_foral, temporal and negative cases.
Actual evidence must be independently reviewed; hash-shaped text cannot prove
reviewer authenticity.

After a hardware pilot, freeze a policy with `cases_sha256`, independent
`freeze_evidence_sha256`, numeric `minimums` for recall20/mrr10/ndcg10/precision5,
`maximum_negative_false_positive_rate` (a maximum, measured on negative cases
only), and `stratum_minimums` for every language and tier. Keep an independently
timestamped policy SHA256 receipt before holdout. Rankings JSON maps each
holdout case ID to a list of unique section-version IDs. Run:

```powershell
python -m evaluation.evaluate --cases reviewed-cases.json --rankings rankings.json --frozen-policy frozen-policy.json --policy-sha256 RECEIPT_SHA256 --output quality-report.json
```

Metric success alone does not activate LAYA ranking. Runtime permits shadow
only; changing that requires the separately approved comparison and adoption
decision. Missing official source coverage blocks first release regardless of
retrieval scores.
