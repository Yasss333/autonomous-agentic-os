# Autonomous Agentic OS

A portable starter for the CRM internship prototype. Open this folder as the project root in Codex or another IDE. [AGENTS.md](AGENTS.md) records the decisions and next task. [The three-phase plan](docs/Three_Phase_Implementation_Plan.md) contains the detailed build and review checklist.

## Current state (Phase 1 slice)

The app now has: invited-account login with first-login password change, a Neon/Postgres schema with migrations, seeded sample CRM data, and a working CRM UI (leads, companies, follow-up tasks, activities, search). AI generation is **not** connected yet — that is Phase 2.

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

## Verify and hand off

- `cd web; npm run build` — production frontend build.
- `curl http://localhost:5173/api/health` — expect `{"status":"ok","database":"configured"}`.
- Login → change password → create a lead → add an activity and task → refresh: data persists.
- Stale `version` on PATCH returns 409; invalid payloads return 422; no session returns 401.

Verified on 14 Nov 2026 against local Postgres 17 + pgvector (Docker, port 5433): migrations, seed, invite provisioning, login/logout/password change, lead CRUD with optimistic locking, activities, tasks, company links, and search. The same code runs against Neon once `DATABASE_URL` points there — Neon has not been exercised yet.

Transfer the whole repo folder or clone the Git bundle. Start the new agent with: “Read AGENTS.md and README.md. Continue from the Phase 1 exit: point DATABASE_URL at Neon, then start Phase 2.” Keep private environment values outside the transfer.

Next work: Phase 2 — LiteLLM/OpenRouter provider calls, sponsored-task allowance, outbound worker polling, LangGraph generate→QA→repair loop, and the Docker QA harness.
