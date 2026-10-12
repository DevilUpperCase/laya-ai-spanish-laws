# Optional domain hosting

The owner currently wants a local installation. Domain hosting is optional configuration for another operator who downloads this project; it does not change the full nationwide first-release evidence requirements. No public server or domain has been deployed.

## Keep the local default

Use `http://127.0.0.1:3000`. The configured Windows logon supervisor, local Auth/database/model/scanner services and normal password login work without a domain. No domain command is required for local users.

## Prepare a future domain

Choose a hostname you control, for example `legal.example.org`. Preparation validates it and writes only an ignored profile; it does not change the active local configuration:

```powershell
.venv/Scripts/python.exe scripts/configure_domain.py --domain legal.example.org
```

When the server, DNS and trusted TLS/proxy arrangement are ready, `--apply` updates only `LAYA_DOMAIN`, `APP_ENV=production` and HTTPS `CORS_ORIGINS` in the existing ignored `.env`. It validates the existing production credentials/model/scanner prerequisites without printing them. All other settings and secrets are preserved. Restart the API/web after applying; browser cookies become Secure and plain HTTP login is no longer appropriate.

```powershell
.venv/Scripts/python.exe scripts/configure_domain.py --domain legal.example.org --apply
$env:LAYA_DOMAIN = 'legal.example.org'
caddy run --config infra/Caddyfile.production
```

Run this production Caddy configuration **on the host**, where its fixed upstream `127.0.0.1:3000` is reachable. It uses the hostname environment variable, public certificate automation and HTTPS headers. Caddy's admin endpoint is disabled. The loopback Docker Caddy service is a local-CA rehearsal and is a separate deployment choice; it is not the host production configuration.

Before exposing the site, configure A/AAAA DNS to the host, permit the necessary TLS/HTTP certificate-challenge traffic, review firewall and trusted proxy behavior, use actual production accounts/key custody, and complete the confirmed release gates. Keep API, PostgreSQL, Auth, ClamAV and LAYA listeners private. This command does not provision DNS, register a domain, publish, reset credentials or authorize release.

## Other hosts and downloaded copies

Generated credentials, private documents, session files, model caches, backups and local CA keys are ignored and must never be shipped with the repository. Each installation initializes its own database roles, Auth account, signing keys and backup key. Locks and model manifests determine dependencies; source snapshots are public evidence, not client data.

Python scripts resolve the project root from their own location and use `sys.executable`, so the same CLI code can run under a Linux virtual environment with `.venv/bin/python` in place of `.venv/Scripts/python.exe`. Use Node 22, Python 3.12, uv, Docker Engine/Compose and local Tesseract with the pinned language files. Linux must supply a compatible local Tesseract library; the Windows binary installation is not portable. Windows scheduled-task scripts apply only to Windows; on Linux, arrange a limited service/timer that invokes `scripts/local_stack.py serve` and `scripts/scheduled_backup.py` from the project root. Keep their existing ownership/maintenance locks.

The Docker Compose files define the pinned PostgreSQL, Auth, scanner and local TLS services. The current Python/Node/model processes run on the host; there is no fully containerized application image. A Linux deployment has not been rehearsed in this Windows session. Test platform dependencies, local model integrity, scanner, backup/restore and the normal-login browser workflow before using a downloaded copy with client data.

The simple login-attempt limiter currently sees the fixed proxy address and can share a limit between users. A larger domain deployment needs an explicitly trusted proxy/client-IP and distributed throttling design; do not trust arbitrary forwarded headers. Production identity recovery/invitation/suspension, multiple workspaces and service monitoring need operator setup.

See [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) for bootstrap and operations, [REMAINING_WORK.md](REMAINING_WORK.md) for release evidence and [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md) for the lawyer/staff review workflow.
