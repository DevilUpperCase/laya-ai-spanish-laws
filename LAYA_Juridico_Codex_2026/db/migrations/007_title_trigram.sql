CREATE INDEX instrument_title_trigram ON legal.instruments USING gin(title gin_trgm_ops);
ANALYZE legal.instruments;
