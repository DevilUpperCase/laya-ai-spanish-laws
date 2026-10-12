CREATE SCHEMA private;
CREATE TABLE private.tenants (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL);
CREATE TABLE private.tenant_members (
 tenant_id uuid REFERENCES private.tenants(id), user_id uuid NOT NULL,
 role text NOT NULL CHECK(role IN ('admin','lawyer','reader')), PRIMARY KEY(tenant_id,user_id)
);
CREATE FUNCTION private.member_role(tid uuid) RETURNS text LANGUAGE sql STABLE SECURITY DEFINER
 SET search_path = pg_catalog,private AS $$
 SELECT role FROM private.tenant_members
 WHERE tenant_id=tid AND user_id=nullif(current_setting('app.user_id',true),'')::uuid
 $$;
CREATE FUNCTION private.can_read(tid uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT tid=nullif(current_setting('app.tenant_id',true),'')::uuid
 AND (private.member_role(tid) IS NOT NULL OR current_user='laya_worker')
 $$;
CREATE FUNCTION private.can_write(tid uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT private.can_read(tid) AND (private.member_role(tid) IN ('admin','lawyer') OR current_user='laya_worker')
 $$;
REVOKE ALL ON FUNCTION private.member_role(uuid),private.can_read(uuid),private.can_write(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.member_role(uuid),private.can_read(uuid),private.can_write(uuid) TO laya_api,laya_worker;
CREATE TABLE private.documents (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES private.tenants(id), uploader uuid NOT NULL,
 filename text NOT NULL, mime_type text NOT NULL, object_key text NOT NULL, sha256 text NOT NULL,
 parse_status text NOT NULL DEFAULT 'queued', failure_code text, idempotency_key text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), deletion_epoch integer NOT NULL DEFAULT 0,
 deleted_at timestamptz, purge_due_at timestamptz, purged_at timestamptz,
 UNIQUE(id,tenant_id), UNIQUE(tenant_id,idempotency_key)
);
CREATE TABLE private.chunks (
 document_id uuid NOT NULL, tenant_id uuid NOT NULL, page_number integer NOT NULL,
 text text NOT NULL, ocr_uncertain boolean NOT NULL DEFAULT false,
 PRIMARY KEY(document_id,page_number),
 FOREIGN KEY(document_id,tenant_id) REFERENCES private.documents(id,tenant_id)
);
CREATE TABLE private.jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), document_id uuid NOT NULL, tenant_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN ('extract','purge')), status text NOT NULL DEFAULT 'queued',
 attempts integer NOT NULL DEFAULT 0, lease_until timestamptz, lease_token uuid,
 next_attempt timestamptz NOT NULL DEFAULT now(), deletion_epoch integer NOT NULL,
 failure_code text, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(document_id,tenant_id) REFERENCES private.documents(id,tenant_id),
 UNIQUE(document_id,kind,deletion_epoch)
);
CREATE TABLE private.deletion_records (
 document_id uuid PRIMARY KEY, tenant_id uuid NOT NULL, deleted_at timestamptz NOT NULL,
 purge_due_at timestamptz NOT NULL, purged_at timestamptz,
 backup_expiry_at timestamptz NOT NULL, deletion_epoch integer NOT NULL
);
CREATE INDEX document_tenant ON private.documents(tenant_id);
CREATE INDEX private_chunks_tenant ON private.chunks(tenant_id,document_id);
CREATE INDEX jobs_queue ON private.jobs(status,next_attempt,lease_until);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['documents','chunks','jobs','deletion_records'] LOOP
 EXECUTE format('ALTER TABLE private.%I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE private.%I FORCE ROW LEVEL SECURITY',t);
 END LOOP;
END $$;
CREATE POLICY documents_read ON private.documents FOR SELECT USING(private.can_read(tenant_id));
CREATE POLICY documents_insert ON private.documents FOR INSERT WITH CHECK(private.can_write(tenant_id) AND deleted_at IS NULL AND uploader=nullif(current_setting('app.user_id',true),'')::uuid);
CREATE POLICY documents_update ON private.documents FOR UPDATE USING(private.can_write(tenant_id)) WITH CHECK(private.can_write(tenant_id));
CREATE POLICY chunks_read ON private.chunks FOR SELECT USING(private.can_read(tenant_id) AND EXISTS(SELECT 1 FROM private.documents d WHERE d.id=document_id AND d.tenant_id=chunks.tenant_id AND d.deleted_at IS NULL));
CREATE POLICY chunks_insert ON private.chunks FOR INSERT WITH CHECK(private.can_write(tenant_id) AND EXISTS(SELECT 1 FROM private.documents d WHERE d.id=document_id AND d.tenant_id=chunks.tenant_id AND d.deleted_at IS NULL));
CREATE POLICY chunks_delete ON private.chunks FOR DELETE USING(private.can_write(tenant_id));
CREATE POLICY jobs_read ON private.jobs FOR SELECT USING(private.can_read(tenant_id));
CREATE POLICY jobs_insert ON private.jobs FOR INSERT WITH CHECK(private.can_write(tenant_id));
CREATE POLICY jobs_update ON private.jobs FOR UPDATE USING(private.can_write(tenant_id)) WITH CHECK(private.can_write(tenant_id));
CREATE POLICY deletions_read ON private.deletion_records FOR SELECT USING(private.can_read(tenant_id));
CREATE POLICY deletions_insert ON private.deletion_records FOR INSERT WITH CHECK(private.can_write(tenant_id));
CREATE POLICY deletions_update ON private.deletion_records FOR UPDATE USING(private.can_write(tenant_id)) WITH CHECK(private.can_write(tenant_id));
CREATE FUNCTION private.lease_job() RETURNS SETOF private.jobs LANGUAGE sql SECURITY DEFINER
 SET search_path=pg_catalog,private AS $$
 UPDATE private.jobs SET status='processing', attempts=attempts+1,
 lease_until=now()+interval '5 minutes',lease_token=gen_random_uuid()
 WHERE id=(SELECT id FROM private.jobs WHERE ((status IN ('queued','retry') AND next_attempt<=now())
 OR (status='processing' AND lease_until<now())) AND (attempts<5 OR kind='purge')
 ORDER BY CASE kind WHEN 'purge' THEN 0 ELSE 1 END, created_at
 FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *
 $$;
REVOKE ALL ON FUNCTION private.lease_job() FROM PUBLIC;
GRANT USAGE ON SCHEMA private TO laya_api,laya_worker;
GRANT EXECUTE ON FUNCTION private.lease_job() TO laya_worker;
GRANT SELECT,INSERT,UPDATE ON private.documents,private.jobs,private.deletion_records TO laya_api;
GRANT SELECT ON private.chunks TO laya_api;
GRANT SELECT,INSERT,UPDATE,DELETE ON private.chunks TO laya_worker;
GRANT SELECT,UPDATE ON private.documents,private.jobs,private.deletion_records TO laya_worker;
