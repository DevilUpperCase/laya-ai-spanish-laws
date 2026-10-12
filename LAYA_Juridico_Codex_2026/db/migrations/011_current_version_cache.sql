-- Current-date selection only; historical and verified-effective queries retain their filters.
CREATE INDEX latest_version_nulls_last ON legal.section_versions(section_id,consolidation_date DESC NULLS LAST,source_order DESC,id DESC) INCLUDE(publication_date);
CREATE TABLE legal.current_versions_cache(section_id text PRIMARY KEY REFERENCES legal.sections(id),version_id text NOT NULL REFERENCES legal.section_versions(id));
CREATE UNIQUE INDEX current_version_id ON legal.current_versions_cache(version_id);
CREATE TABLE legal.current_cache_metadata(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),as_of date NOT NULL);
GRANT SELECT ON legal.current_versions_cache,legal.current_cache_metadata TO laya_api,laya_worker;
GRANT SELECT,INSERT,UPDATE ON legal.current_versions_cache,legal.current_cache_metadata TO laya_ingest;
CREATE FUNCTION legal.refresh_current_versions() RETURNS void LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,legal AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(149728);
 DELETE FROM legal.current_versions_cache;
 INSERT INTO legal.current_versions_cache
 SELECT DISTINCT ON(section_id) section_id,id FROM legal.section_versions WHERE publication_date<=current_date
 ORDER BY section_id,consolidation_date DESC NULLS LAST,source_order DESC,id DESC;
 INSERT INTO legal.current_cache_metadata VALUES(true,current_date) ON CONFLICT(singleton) DO UPDATE SET as_of=excluded.as_of;
END $$;
REVOKE ALL ON FUNCTION legal.refresh_current_versions() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION legal.refresh_current_versions() TO laya_ingest;
SELECT legal.refresh_current_versions();
ANALYZE legal.current_versions_cache;
