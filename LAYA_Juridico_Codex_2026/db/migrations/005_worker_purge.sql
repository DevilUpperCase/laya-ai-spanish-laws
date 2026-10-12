-- DELETE also needs row visibility. The API still cannot read tombstoned chunks.
CREATE POLICY chunks_worker_cleanup_select ON private.chunks FOR SELECT TO laya_worker
 USING(private.can_read(tenant_id));
