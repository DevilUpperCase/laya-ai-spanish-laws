ALTER TABLE legal.instruments ADD COLUMN ingestion_warnings jsonb NOT NULL DEFAULT '[]';
ALTER TABLE legal.section_versions ADD COLUMN official_url text;
