ALTER TABLE legal.section_versions ADD COLUMN source_order integer NOT NULL DEFAULT 0;
CREATE INDEX latest_version_order ON legal.section_versions(section_id,consolidation_date DESC,source_order DESC,id DESC) INCLUDE(publication_date);
ANALYZE legal.section_versions;
ANALYZE legal.chunks;
ANALYZE legal.sections;
ANALYZE legal.instruments;
