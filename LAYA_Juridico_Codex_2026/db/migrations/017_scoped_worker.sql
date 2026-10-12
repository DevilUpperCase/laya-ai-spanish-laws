-- Targeted canary/recovery runs must not consume another workspace's queued job.
CREATE FUNCTION private.lease_document_job(target uuid) RETURNS SETOF private.jobs LANGUAGE sql SECURITY DEFINER
 SET search_path=pg_catalog,private AS $$
 UPDATE private.jobs SET status='processing',attempts=attempts+1,lease_until=now()+interval '5 minutes',lease_token=gen_random_uuid()
 WHERE id=(SELECT id FROM private.jobs WHERE document_id=target AND
 ((status IN ('queued','retry') AND next_attempt<=now()) OR (status='processing' AND lease_until<now()))
 AND (attempts<5 OR kind='purge')
 ORDER BY CASE kind WHEN 'purge' THEN 0 WHEN 'extract' THEN 1 ELSE 2 END,created_at
 FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *
 $$;
REVOKE ALL ON FUNCTION private.lease_document_job(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.lease_document_job(uuid) TO laya_worker;
CREATE OR REPLACE FUNCTION private.recover_exhausted_jobs() RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,private AS $$
DECLARE recovered integer;
BEGIN
 WITH expired AS (
 UPDATE private.jobs SET status='failed',failure_code='LEASE_EXHAUSTED',lease_until=NULL,lease_token=NULL
 WHERE kind IN ('extract','index') AND attempts>=5 AND
 ((status='processing' AND lease_until<now()) OR status IN ('queued','retry'))
 RETURNING document_id,tenant_id,deletion_epoch,kind)
 UPDATE private.documents d SET parse_status='failed',failure_code='LEASE_EXHAUSTED'
 FROM expired e WHERE e.kind='extract' AND d.id=e.document_id AND d.tenant_id=e.tenant_id
 AND d.deleted_at IS NULL AND d.deletion_epoch=e.deletion_epoch;
 GET DIAGNOSTICS recovered=ROW_COUNT;
 RETURN recovered;
END $$;
