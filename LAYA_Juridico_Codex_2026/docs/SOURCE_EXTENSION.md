# Extending official-source ingestion

BOE, DOGC and DOG have concrete publisher adapters. Directory entries for other publishers are discovery leads. They must not be presented as implemented nationwide ingestion. The common protocol in `services/ingest/ingest/contracts.py` separates discovery, bounded fetch and parsing; `pipeline.py` commits immutable original artifacts, instrument/section versions and passages atomically.

## Complete publisher adapter

1. Identify the official normative catalogue and reuse terms. Capture official documentation, representative original publications, all supported languages, dates, pagination and history boundaries. Avoid personal administrative announcements, job appointments and individual notices.
2. Add a publisher module implementing `discover`, `fetch`, `parse` and `close`. Exact approved hosts must constrain every redirect. Test pagination until exhaustion, source totals/date gaps, duplicate identities, format variants, translations, annexes and malformed metadata against actual captured fixtures.
3. Keep publication and effectiveness distinct. Do not invent commencement dates, article numbers or translations. Namespace identities where publishers can reuse the same external identifier. Store the actual official reference and URL per language/version.
4. Resolve territories by exact official geographic identifiers, including province, municipality and relevant island/foral institutions. Homonymous names require explicit IDs. Do not assign municipal legislation to the whole province as a substitute.
5. Register the adapter and source, run bounded imports, reconcile the official inventory against integrated publications, then audit the full required current/history range. Any failure leaves the source partial and must not advance complete-source freshness.
6. A professional/source reviewer supplies the audit artifact and hash, reuse approval, unavailable-history evidence and geographic mappings. `scripts/verify_package.py --release` checks these artifacts; only actual reviews can satisfy release gates.

## Enumerated manifest importer

For a publisher with no complete discovery adapter, `scripts/ingest_manifest.py sources/<reviewed-manifest>.json` imports a **finite list of reviewed norms**. It supports HTML with one publisher-specific body selector and PDF through the isolated extraction worker after configured malware scanning. Scanned PDFs are rejected until an audited OCR import path is provided.

This path supports any existing exact geographic ID, including municipal/island/provincial IDs. It deliberately adds `ENUMERATED_MANIFEST_IS_NOT_COMPLETE_DISCOVERY` and history/annex gaps. A list of known norms does not prove there are no missing norms.

```json
{
  "source_id": "OFFICIAL_PUBLISHER_ID",
  "name": "Publisher name",
  "official_url": "https://publisher.example/",
  "terms_url": "https://publisher.example/terms",
  "allowed_hosts": ["publisher.example"],
  "reviewer": "Actual reviewer name",
  "review_evidence": "review.md",
  "review_sha256": "SHA256 of the actual review artifact",
  "publications": [{
    "external_id": "Publisher instrument identifier",
    "official_reference": "Official publication reference",
    "official_url": "https://publisher.example/norm/identifier",
    "title": "Official title",
    "publication_date": "2026-01-01",
    "jurisdiction_id": "ES-MUN-EXACT_INE_CODE",
    "language": "es",
    "legal_type": "Ordenanza",
    "normative": true,
    "format": "html",
    "selector": "article.normative-body"
  }]
}
```

The example is documentation and cannot pass validation as written. Review files and manifests must be inside `sources`; hashes must match. `artifact_sha256` can bind an original to reviewed bytes. `version_date` is optional publisher version metadata, never inferred effectiveness. URLs cannot contain credentials or escape the exact host list. Original bodies are preserved by content hash. This tool validates evidence structure; it cannot authenticate professional identity.

## Current evidence

The BOE gap-recovery report resolves the earlier 45 parser/size/jurisdiction failures. DOGC reconciliation recovered all 14 preview failures; the full original-publication catalogue backfill is now supervised, with missing-language warnings and source history/annex limits retained. DOGC's original-language Akoma Ntoso and DOG's Spanish/Galician general-disposition RSS are real imports with explicit limits. Galicia's captured RSS window is stale relative to the run date; its archive and freshness need reconciliation. Nationwide publisher entrypoint captures have remaining transport/redirect failures. Navarra/Bizkaia/Gipuzkoa research identifies official services, but does not yet provide complete source adapters or reviewed archival coverage.

Consult the [official BOE API](https://www.boe.es/datosabiertos/api/api.php), [DOGC open-data description](https://dogc.gencat.cat/es/serveis/Dades_obertes/), [Navarra official normative services](https://www.navarra.es/es/normativa) and [Bizkaia official bulletin](https://www.bizkaia.eus/es/bob). Their catalogues and notices determine what must be audited; the directory itself is not coverage evidence.
