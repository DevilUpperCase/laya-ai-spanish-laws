-- Opaque browser sessions; only the trusted API role can access their hashes.
CREATE SCHEMA browser_auth;
REVOKE ALL ON SCHEMA browser_auth FROM PUBLIC;
CREATE TABLE browser_auth.sessions (
 digest text PRIMARY KEY CHECK(length(digest)=64), user_id uuid NOT NULL,
 email text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL
);
CREATE INDEX session_expiry ON browser_auth.sessions(expires_at);
GRANT USAGE ON SCHEMA browser_auth TO laya_api;
GRANT SELECT,INSERT,DELETE ON browser_auth.sessions TO laya_api;
CREATE FUNCTION private.my_workspaces() RETURNS TABLE(id uuid,name text,role text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,private AS $$
 SELECT t.id,t.name,m.role FROM private.tenants t JOIN private.tenant_members m ON m.tenant_id=t.id
 WHERE m.user_id=nullif(current_setting('app.user_id',true),'')::uuid ORDER BY t.name,t.id
$$;
REVOKE ALL ON FUNCTION private.my_workspaces() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.my_workspaces() TO laya_api;
