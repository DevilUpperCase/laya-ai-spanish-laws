CREATE TABLE private.folders (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id uuid NOT NULL REFERENCES private.tenants(id),
 name text NOT NULL CHECK(length(name) BETWEEN 1 AND 200),parent_id uuid,UNIQUE(id,tenant_id),
 FOREIGN KEY(parent_id,tenant_id) REFERENCES private.folders(id,tenant_id)
);
ALTER TABLE private.documents ADD COLUMN folder_id uuid;
ALTER TABLE private.documents ADD COLUMN trashed_at timestamptz;
ALTER TABLE private.documents ADD CONSTRAINT document_folder FOREIGN KEY(folder_id,tenant_id) REFERENCES private.folders(id,tenant_id);
CREATE TABLE private.notebooks (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id uuid NOT NULL REFERENCES private.tenants(id),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 200),folder_id uuid,UNIQUE(id,tenant_id),
 FOREIGN KEY(folder_id,tenant_id) REFERENCES private.folders(id,tenant_id)
);
CREATE TABLE private.notes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id uuid NOT NULL,notebook_id uuid NOT NULL,
 document_id uuid,page_number integer,start_offset integer,end_offset integer,
 body text NOT NULL CHECK(length(body)<=50000),revision integer NOT NULL DEFAULT 1,
 updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(notebook_id,tenant_id) REFERENCES private.notebooks(id,tenant_id),
 FOREIGN KEY(document_id,tenant_id) REFERENCES private.documents(id,tenant_id),
 CHECK((page_number IS NULL AND start_offset IS NULL AND end_offset IS NULL) OR
 (document_id IS NOT NULL AND page_number>=1 AND start_offset>=0 AND end_offset>start_offset))
);
CREATE TABLE private.saved_references (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id uuid NOT NULL,notebook_id uuid NOT NULL,
 section_version_id text NOT NULL REFERENCES legal.section_versions(id),document_id uuid,
 FOREIGN KEY(notebook_id,tenant_id) REFERENCES private.notebooks(id,tenant_id),
 FOREIGN KEY(document_id,tenant_id) REFERENCES private.documents(id,tenant_id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['folders','notebooks','notes','saved_references'] LOOP
 EXECUTE format('ALTER TABLE private.%I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE private.%I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY read ON private.%I FOR SELECT USING(private.can_read(tenant_id))',t);
 EXECUTE format('CREATE POLICY write ON private.%I FOR ALL USING(private.can_write(tenant_id)) WITH CHECK(private.can_write(tenant_id))',t);
 EXECUTE format('GRANT SELECT,INSERT,UPDATE,DELETE ON private.%I TO laya_api',t);
 END LOOP;
END $$;
DROP POLICY read ON private.notes;
CREATE POLICY read ON private.notes FOR SELECT USING(private.can_read(tenant_id) AND
 (current_user='laya_worker' OR document_id IS NULL OR EXISTS(SELECT 1 FROM private.documents d WHERE d.id=document_id AND d.tenant_id=notes.tenant_id AND d.deleted_at IS NULL)));
-- FOR ALL policies also participate in SELECT: exclude permanent tombstones there too.
DROP POLICY write ON private.notes;
CREATE POLICY write ON private.notes FOR ALL USING(private.can_write(tenant_id) AND
 (document_id IS NULL OR EXISTS(SELECT 1 FROM private.documents d WHERE d.id=document_id AND d.tenant_id=notes.tenant_id AND d.deleted_at IS NULL)))
 WITH CHECK(private.can_write(tenant_id) AND
 (document_id IS NULL OR EXISTS(SELECT 1 FROM private.documents d WHERE d.id=document_id AND d.tenant_id=notes.tenant_id AND d.deleted_at IS NULL)));
GRANT SELECT,DELETE ON private.notes,private.saved_references TO laya_worker;
CREATE POLICY notes_worker_purge ON private.notes FOR DELETE USING(current_user='laya_worker' AND private.can_write(tenant_id));
CREATE POLICY references_worker_purge ON private.saved_references FOR DELETE USING(current_user='laya_worker' AND private.can_write(tenant_id));
CREATE INDEX notes_notebook ON private.notes(tenant_id,notebook_id);
CREATE INDEX documents_library ON private.documents(tenant_id,trashed_at,created_at);
