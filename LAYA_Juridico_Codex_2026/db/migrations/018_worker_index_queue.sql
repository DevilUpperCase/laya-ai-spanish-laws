-- Extraction publishes a durable indexing job in the same transaction.
-- Existing jobs_insert policy still requires the worker's active tenant.
GRANT INSERT ON private.jobs TO laya_worker;
