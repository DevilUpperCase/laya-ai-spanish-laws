-- Filesystem storage is private and reachable only through the authorization gateway.
-- Self-host Supabase deployments additionally protect storage.objects if present.
DO $$ BEGIN
 IF to_regclass('storage.objects') IS NOT NULL THEN
  EXECUTE 'CREATE POLICY laya_client_read ON storage.objects FOR SELECT TO authenticated USING (bucket_id=''client-private'' AND EXISTS(SELECT 1 FROM private.documents d WHERE d.object_key=name AND d.deleted_at IS NULL AND private.can_read(d.tenant_id)))';
 END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
