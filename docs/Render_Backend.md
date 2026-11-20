# Render backend

The API deploys from `codex/render-backend` to a free Python web service in
ayush's Render workspace (`tea-dc084897lnhs739vaio0`), Singapore region.

- Build: `pip install -r api/requirements.txt`
- Start: `python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Health: `/api/health` (configuration check; not a database connectivity probe)
- Runtime: Python 3.13.5, one process; automatic deployments disabled.
- Database: separate Neon `agent-os` project, PostgreSQL 17, Singapore.

Set pooled `DATABASE_URL`, direct `DATABASE_DIRECT_URL`, `APP_ENV=production`,
`LOCAL_DEMO=0`, `RUNNER_FIXTURE=0`, secure cookies, a random `RUNNER_TOKEN`,
OpenRouter credentials, and Clerk issuer/authorized parties in Render's secret
environment settings. Never commit their values. Only allow the deployed Vercel
origin. Existing password sessions cannot bypass configured Clerk verification.

Apply migrations using `scripts/migrate.py` and seed synthetic records with
`scripts/seed.py` using the new database URLs. A Clerk account must be explicitly
linked with `scripts/provision_user.py EMAIL --clerk-user-id USER_ID` before it
can access the workspace. Do not copy local demo passwords into production.

Validation before deployment: 12 API authentication, schema, and input validation
tests passed. Verify the live health endpoint, unauthorized requests, and a real
database read after deploying. Signed-in testing requires a linked Clerk user.

The Docker worker is a separate deployment; do not run generated code inside the
API service. Free Render instances sleep and lose in-memory reviewer API keys on
restart. Reattach those keys after a restart. Persistent application data stays
in Neon.

Rollback: select a previous successful deployment in Render. For the first
deployment, suspend the service if verification fails. Keep the Neon data;
do not reverse migrations or delete the database to roll back application code.

## Verified deployment, 20 November 2026

- Render service: `srv-dc08aa88v5cc738sk3og`, plan `free`, region `singapore`.
- API: https://agent-os-api-hvly.onrender.com
- Deployment: `dep-dc08ab08v5cc738sk650`, source commit `b2c886f`.
- Dashboard: https://dashboard.render.com/web/srv-dc08aa88v5cc738sk3og
- Neon project: `twilight-night-83535756`, database `agent_os`.
- All four migrations applied; seeded 8 companies, 30 leads, 20 activities,
  and 15 tasks. No real customer records or local demo passwords copied.
- Vercel project-level rewrite `^/api/(.*)$` forwards to the Render API.
  Routing version: `05875b7f-12e4-4d2d-979e-8d2040f24ec4`.
- Health returned 200 directly and through Vercel. Anonymous `/api/me` and
  worker claims returned 401. Legacy password login returned 404. An
  authenticated heartbeat with a nonexistent lease queried Neon and returned
  the expected 409 without claiming a job. Untrusted origins returned 403.
- Pending: explicitly link an invited Clerk user, verify a signed-in app
  journey and live model request, then deploy the separate Docker worker.

The Vercel rewrite is stored in project routing settings, not `vercel.json`.
To undo frontend API routing, remove that rule or restore the prior routing
version. No frontend assets were rebuilt for this backend deployment.
