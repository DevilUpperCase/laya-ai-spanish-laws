CREATE INDEX chunks_missing_embedding ON legal.chunks(id) INCLUDE(version_id) WHERE embedding IS NULL;
-- A fifth crashed extraction must become visibly failed, never permanently processing.
CREATE FUNCTION private.recover_exhausted_jobs() RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,private AS $$
DECLARE recovered integer;
BEGIN
 WITH expired AS (
 UPDATE private.jobs SET status='failed',failure_code='LEASE_EXHAUSTED',lease_until=NULL,lease_token=NULL
 WHERE kind='extract' AND attempts>=5 AND
 ((status='processing' AND lease_until<now()) OR status IN ('queued','retry'))
 RETURNING document_id,tenant_id,deletion_epoch)
 UPDATE private.documents d SET parse_status='failed',failure_code='LEASE_EXHAUSTED'
 FROM expired e WHERE d.id=e.document_id AND d.tenant_id=e.tenant_id
 AND d.deleted_at IS NULL AND d.deletion_epoch=e.deletion_epoch;
 GET DIAGNOSTICS recovered=ROW_COUNT;
 RETURN recovered;
END $$;
REVOKE ALL ON FUNCTION private.recover_exhausted_jobs() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.recover_exhausted_jobs() TO laya_worker;
