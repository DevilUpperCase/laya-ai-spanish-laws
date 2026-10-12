INSERT INTO legal.sources(id,name,official_url,terms_url,adapter,limitations) VALUES
 ('BOE_DAILY','BOE all daily items','https://www.boe.es/diario_boe/','https://www.boe.es/informacion/aviso_legal/','boe_bulletin','["Full available history and source terms require review"]'),
 ('BORME_DAILY','BORME all daily items','https://www.boe.es/diario_borme/','https://www.boe.es/informacion/aviso_legal/','boe_bulletin','["Registry PDFs can contain several announcements; subitem/annex audit pending"]') ON CONFLICT DO NOTHING;
CREATE TABLE legal.bulletin_items (
 id text PRIMARY KEY,source_id text NOT NULL REFERENCES legal.sources(id),external_id text NOT NULL,
 title text NOT NULL,publication_date date NOT NULL,jurisdiction_id text NOT NULL REFERENCES legal.jurisdictions(id),
 category text NOT NULL,normative boolean NOT NULL,official_url text NOT NULL,pdf_url text,
 status text NOT NULL DEFAULT 'discovered',failure_code text,text text,
 search_vector tsvector,embedding vector(1024),embedding_revision text,
 UNIQUE(source_id,external_id)
);
CREATE TABLE legal.bulletin_chunks (
 id text PRIMARY KEY,item_id text NOT NULL REFERENCES legal.bulletin_items(id),
 ordinal integer NOT NULL,start_offset integer NOT NULL,end_offset integer NOT NULL,passage text NOT NULL,
 search_vector tsvector NOT NULL,embedding vector(1024),embedding_revision text,
 UNIQUE(item_id,ordinal)
);
CREATE TABLE legal.source_periods (
 source_id text REFERENCES legal.sources(id),publication_date date NOT NULL,
 expected_count integer,expected_assets integer,status text NOT NULL,summary_sha256 text,
 reconciled_at timestamptz NOT NULL DEFAULT now(),failure_code text,
 PRIMARY KEY(source_id,publication_date)
);
GRANT SELECT ON legal.bulletin_items,legal.bulletin_chunks,legal.source_periods TO laya_api,laya_worker;
GRANT SELECT,INSERT,UPDATE,DELETE ON legal.bulletin_items,legal.bulletin_chunks,legal.source_periods TO laya_ingest;
GRANT INSERT,UPDATE ON legal.bulletin_chunks TO laya_worker;
CREATE INDEX bulletin_chunks_fts ON legal.bulletin_chunks USING gin(search_vector);
CREATE INDEX bulletin_period ON legal.bulletin_items(source_id,publication_date);
