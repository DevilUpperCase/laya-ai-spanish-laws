CREATE TABLE legal.publication_assets (
 id text PRIMARY KEY,source_id text NOT NULL REFERENCES legal.sources(id),external_id text NOT NULL,
 official_url text NOT NULL,mime_type text NOT NULL,sha256 text NOT NULL CHECK(length(sha256)=64),
 object_key text NOT NULL,kind text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(source_id,external_id,official_url,sha256)
);
GRANT SELECT ON legal.publication_assets TO laya_api,laya_worker;
GRANT SELECT,INSERT,UPDATE ON legal.publication_assets TO laya_ingest;
