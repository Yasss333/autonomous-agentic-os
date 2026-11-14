# Autonomous Agentic OS

A portable starter for the CRM internship prototype. Open this folder as the project root in Codex or another IDE. [AGENTS.md](AGENTS.md) records the decisions and next task. [The three-phase plan](docs/Three_Phase_Implementation_Plan.md) contains the detailed build and review checklist.

## Start locally

Use Node.js 22.12+ and Python 3.12 or 3.13. In a PowerShell terminal at the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir api --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd web
npm ci
npm run dev
```

On macOS or Linux, replace the Windows venv executable with `.venv/bin/python`. Open [the landing page](http://localhost:5173) and choose **Open prototype workspace**. It should show **FastAPI is connected.** The API docs are at [port 8000](http://127.0.0.1:8000/docs).

## Verify and hand off

Run `npm run build` from `web/`. With both services running, request `http://localhost:5173/api/health` and expect `{"status":"ok"}`. The starter runs without a Neon login, OpenRouter key, or Docker.

The initial handoff passed the React production build, `pip check`, and live HTTP checks for the landing page, workspace, and Vite-to-FastAPI proxy. The HTTP check used port 15173 because port 5173 was occupied. If needed, run `npm run dev -- --port 15173` and open that port instead.

Transfer the whole repo folder or clone the Git bundle. Start the new agent with: “Read AGENTS.md and README.md. Continue Phase 1 from the Neon and invited-login slice.” Keep private environment values outside the transfer.

Next work: schema and migrations in Neon, invited login, and one lead flow. The starter screen reports API connectivity only.
