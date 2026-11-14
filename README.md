# Autonomous Agentic OS

A portable starter for the CRM internship prototype. Open this folder as the project root in Codex or another IDE. [AGENTS.md](AGENTS.md) records the decisions and next task. [The three-phase plan](docs/Three_Phase_Implementation_Plan.md) contains the detailed build and review checklist.

## Current state (Phase 2 slice)

Phase 1 is complete and extended with the Phase 2 pipeline: run creation with a one-per-account sponsored allowance (or session-only BYOK OpenRouter key), an outbound laptop worker that claims jobs over HTTPS, a LangGraph generate → Docker QA → capped-repair loop, tool activation/rollback through a registry, sandboxed tool invocation that commits validated CRM operations, and a daily usage panel. Semantic-search embeddings are **not** implemented yet (keyword search only). Real OpenRouter generation is code-complete but unverified — it needs `OPENROUTER_API_KEY` on the worker and a real reviewer key for BYOK runs.

## Start locally

Use Node.js 22.12+ and Python 3.12 or 3.13. In a PowerShell terminal at the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api/requirements.txt
```

Copy `.env.example` to `.env` and set `DATABASE_URL` (Neon pooled URL). For local verification without Neon, a disposable Postgres+pgvector Docker container works:

```powershell
docker run -d --name agentic-os-pg -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=agentic_os -p 5433:5432 pgvector/pgvector:pg17
# then set DATABASE_URL=postgresql://postgres:dev@localhost:5433/agentic_os in .env
```

Apply migrations, seed the demo workspace, and invite an account:

```powershell
.\.venv\Scripts\python.exe scripts/migrate.py
.\.venv\Scripts\python.exe scripts/seed.py
.\.venv\Scripts\python.exe scripts/provision_user.py reviewer@company.com
```

Start the API and the frontend in two terminals:

```powershell
# terminal 1, repo root
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# terminal 2
cd web
npm ci
npm run dev
```

On macOS or Linux, replace the Windows venv executable with `.venv/bin/python`. Open [the landing page](http://localhost:5173), choose **Sign in**, and use the invited email plus the temporary password printed by `provision_user.py`. The first login forces a password change. API docs: [port 8000](http://127.0.0.1:8000/docs).

## The worker (AI generation and tool execution)

Generated code and model calls run on the trusted laptop worker, never in FastAPI. Build the QA image once, then run the worker with env vars:

```powershell
docker build -t agentic-os-qa:latest -f infra/Dockerfile.qa infra/

# same venv as the API
$env:API_BASE_URL='http://127.0.0.1:8000/api'   # public API URL when deployed
$env:RUNNER_TOKEN='...'                        # must match the API's RUNNER_TOKEN
$env:WORKER_ID='laptop-1'
$env:OPENROUTER_API_KEY='sk-or-...'            # owner's sponsored key, worker env only
.\.venv\Scripts\python.exe -m runner.worker
```

For local pipeline verification without a provider key, set `$env:RUNNER_FIXTURE='1'` — the worker then uses a clearly-labelled test-fixture bundle (no model call) so the QA/activation/invocation path can be exercised end to end.

Reviewer BYOK keys are attached in the UI (AI runs tab), live only in API memory under an opaque ref, and are fetchable solely by the worker holding the active lease.

## Verify and hand off

- `cd web; npm run build` — production frontend build.
- `curl http://localhost:5173/api/health` — expect `{"status":"ok","database":"configured"}`.
- Login → change password → create a lead → add an activity and task → refresh: data persists.
- Stale `version` on PATCH returns 409; invalid payloads return 422; no session returns 401.

Verified on 14 Nov 2026 against local Postgres 17 + pgvector (Docker, port 5433): migrations, seed, invite provisioning, login/logout/password change, lead CRUD with optimistic locking, activities, tasks, company links, search, sponsored-allowance enforcement (402 on second run), BYOK attach/detach, idempotent run creation and invocation, lease-based worker claim/heartbeat/result, fixture-tool generation through the Docker QA harness, activation, sandboxed invocation committing 28 follow-up tasks atomically, and deduplicated re-invocation. The same code runs against Neon once `DATABASE_URL` points there — Neon has not been exercised yet. Real OpenRouter calls are untested (no key provided); free-model allowlist defaults are live catalog `:free` IDs fetched 2026-11-14.

Transfer the whole repo folder or clone the Git bundle. Start the new agent with: “Read AGENTS.md and README.md. Continue from the Phase 1 exit: point DATABASE_URL at Neon, then start Phase 2.” Keep private environment values outside the transfer.

Next work: verify real OpenRouter generation with a sponsored key, add embedding-based semantic search (all-MiniLM-L6-v2 on the worker, `vector(384)` already in schema), the failure-matrix checks from P2.16, then Phase 3 hosting.
