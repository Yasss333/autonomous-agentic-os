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
