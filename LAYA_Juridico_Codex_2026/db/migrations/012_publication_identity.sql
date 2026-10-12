-- Original byte identity and reviewed logical publication metadata are distinct.
ALTER TABLE legal.publications ADD COLUMN metadata_sha256 text CHECK(metadata_sha256 IS NULL OR length(metadata_sha256)=64);
ALTER TABLE legal.publications DROP CONSTRAINT publications_source_id_instrument_id_sha256_key;
ALTER TABLE legal.publications ADD CONSTRAINT publications_logical_identity UNIQUE NULLS NOT DISTINCT(source_id,instrument_id,sha256,metadata_sha256);
