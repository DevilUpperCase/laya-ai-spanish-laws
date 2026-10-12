CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA IF NOT EXISTS legal;
CREATE TABLE legal.jurisdictions (
 id text PRIMARY KEY, level text NOT NULL, parent_id text REFERENCES legal.jurisdictions(id),
 name text NOT NULL, official_source_url text NOT NULL, inventory_revision text NOT NULL,
 verified boolean NOT NULL DEFAULT false
);
CREATE TABLE legal.sources (
 id text PRIMARY KEY, name text NOT NULL, official_url text NOT NULL,
 terms_url text NOT NULL, adapter text, audit_status text NOT NULL DEFAULT 'pending',
 last_checked_at timestamptz, last_successful_sync timestamptz, last_integrated_publication date,
 cursor jsonb, limitations jsonb NOT NULL DEFAULT '[]'
);
CREATE TABLE legal.coverage (
 jurisdiction_id text REFERENCES legal.jurisdictions(id), source_id text REFERENCES legal.sources(id),
 status text NOT NULL DEFAULT 'pending', current_from date, current_to date,
 history_from date, history_to date, audit_sha256 text, reviewer text,
 PRIMARY KEY(jurisdiction_id,source_id), CHECK(current_to >= current_from), CHECK(history_to >= history_from)
);
CREATE TABLE legal.instruments (
 id text PRIMARY KEY, source_id text NOT NULL REFERENCES legal.sources(id), external_id text NOT NULL,
 title text NOT NULL, legal_type text NOT NULL, jurisdiction_id text NOT NULL REFERENCES legal.jurisdictions(id),
 eli text, official_reference text NOT NULL, official_url text NOT NULL,
 UNIQUE(source_id, external_id)
);
CREATE TABLE legal.publications (
 id text PRIMARY KEY, instrument_id text NOT NULL REFERENCES legal.instruments(id),
 source_id text NOT NULL REFERENCES legal.sources(id), official_url text NOT NULL,
 publication_date date NOT NULL, fetched_at timestamptz NOT NULL DEFAULT now(),
 sha256 text NOT NULL CHECK(length(sha256)=64), object_key text NOT NULL, format text NOT NULL,
 is_consolidated boolean NOT NULL, source_updated_at text, UNIQUE(source_id,instrument_id,sha256)
);
CREATE TABLE legal.sections (
 id text PRIMARY KEY, instrument_id text NOT NULL REFERENCES legal.instruments(id),
 section_key text NOT NULL, heading text NOT NULL, ordinal integer NOT NULL,
 UNIQUE(instrument_id,section_key)
);
CREATE TABLE legal.section_versions (
 id text PRIMARY KEY, section_id text NOT NULL REFERENCES legal.sections(id),
 publication_id text NOT NULL REFERENCES legal.publications(id), version_ref text NOT NULL,
 publication_date date NOT NULL, consolidation_date date, effective_from date, effective_to date,
 effectiveness_verified boolean NOT NULL DEFAULT false, effectiveness_evidence text,
 text text NOT NULL, language_code text NOT NULL, sha256 text NOT NULL CHECK(length(sha256)=64),
 UNIQUE(section_id,version_ref,sha256), CHECK(effective_to >= effective_from),
 CHECK(NOT effectiveness_verified OR (effective_from IS NOT NULL AND effectiveness_evidence IS NOT NULL))
);
CREATE TABLE legal.relationships (
 from_instrument text REFERENCES legal.instruments(id), to_external_id text NOT NULL,
 kind text NOT NULL, official_evidence_url text NOT NULL, verified boolean NOT NULL DEFAULT false,
 PRIMARY KEY(from_instrument,to_external_id,kind,official_evidence_url)
);
CREATE TABLE legal.chunks (
 id text PRIMARY KEY, version_id text NOT NULL REFERENCES legal.section_versions(id),
 ordinal integer NOT NULL, start_offset integer NOT NULL, end_offset integer NOT NULL,
 passage text NOT NULL, search_vector tsvector NOT NULL,
 UNIQUE(version_id,ordinal), CHECK(start_offset>=0 AND end_offset>start_offset)
);
CREATE INDEX chunks_fts ON legal.chunks USING gin(search_vector);
CREATE INDEX chunks_trigram ON legal.chunks USING gin(passage gin_trgm_ops);
CREATE INDEX version_section ON legal.section_versions(section_id,consolidation_date);
CREATE INDEX instrument_jurisdiction ON legal.instruments(jurisdiction_id);
CREATE TABLE legal.ingest_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id text NOT NULL REFERENCES legal.sources(id),
 started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 status text NOT NULL DEFAULT 'running', expected_count integer, discovered_count integer NOT NULL DEFAULT 0,
 integrated_count integer NOT NULL DEFAULT 0, cursor jsonb, window_start date, window_end date,
 gaps jsonb NOT NULL DEFAULT '[]', failure_code text
);
GRANT USAGE ON SCHEMA legal TO laya_api,laya_ingest,laya_worker;
GRANT SELECT ON ALL TABLES IN SCHEMA legal TO laya_api,laya_worker;
GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA legal TO laya_ingest;
