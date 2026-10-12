ALTER TABLE private.jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE private.jobs ADD CONSTRAINT jobs_kind_check CHECK(kind IN ('extract','purge','index'));
CREATE TABLE private.passage_index (
 id text PRIMARY KEY,document_id uuid NOT NULL,tenant_id uuid NOT NULL,page_number integer NOT NULL,
 start_offset integer NOT NULL,end_offset integer NOT NULL,passage text NOT NULL,ocr_uncertain boolean NOT NULL,
 search_vector tsvector NOT NULL,embedding vector(1024),embedding_revision text,
 FOREIGN KEY(document_id,tenant_id) REFERENCES private.documents(id,tenant_id),
 CHECK(start_offset>=0 AND end_offset>start_offset)
);
ALTER TABLE private.passage_index ENABLE ROW LEVEL SECURITY;
ALTER TABLE private.passage_index FORCE ROW LEVEL SECURITY;
CREATE POLICY read ON private.passage_index FOR SELECT USING(private.can_read(tenant_id) AND EXISTS
 (SELECT 1 FROM private.documents d WHERE d.id=document_id AND d.tenant_id=passage_index.tenant_id AND d.deleted_at IS NULL AND d.trashed_at IS NULL));
CREATE POLICY worker ON private.passage_index FOR ALL USING(current_user='laya_worker' AND private.can_write(tenant_id))
 WITH CHECK(current_user='laya_worker' AND private.can_write(tenant_id) AND EXISTS(SELECT 1 FROM private.documents d WHERE d.id=document_id AND d.tenant_id=passage_index.tenant_id AND d.deleted_at IS NULL));
GRANT SELECT ON private.passage_index TO laya_api;
GRANT SELECT,INSERT,UPDATE,DELETE ON private.passage_index TO laya_worker;
CREATE INDEX private_passage_fts ON private.passage_index USING gin(search_vector);
CREATE INDEX private_passage_documents ON private.passage_index(tenant_id,document_id);
INSERT INTO private.jobs(document_id,tenant_id,kind,deletion_epoch)
 SELECT id,tenant_id,'index',deletion_epoch FROM private.documents WHERE deleted_at IS NULL AND parse_status='ready'
 ON CONFLICT DO NOTHING;
