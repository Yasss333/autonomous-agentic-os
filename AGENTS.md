# Agent handoff

Read [README.md](README.md) and [the three-phase plan](docs/Three_Phase_Implementation_Plan.md) before changing code. These files carry the project decisions between Codex accounts and IDEs.

## Current state

The starter contains a React/Vite landing shell and workspace, a fixed local API proxy, invite-only login, a Neon/Postgres schema with migrations and seeded CRM data, and a working CRM UI. Phase 2 is partially built: run creation with sponsored/BYOK credentials, outbound worker polling with leases, a LangGraph generate→QA→repair loop, a Docker sandbox harness, tool activation/rollback, and sandboxed invocation committing validated CRM operations. Verified end-to-end with RUNNER_FIXTURE=1 (no real model call yet). See README for commands. Remaining Phase 2: real OpenRouter verification, embeddings/semantic search, P2.16 failure matrix. Then Phase 3 hosting.

## Project decisions

- Use React with Vite for the frontend and FastAPI for the backend. The repo's React plan supersedes earlier Next.js material.
- Neon is the sole durable database. Start locally with synthetic data and one invite-only demo workspace. Use exact designated company emails.
- Keep public hosting on free tiers. Vercel and Render are candidates. The owner's trusted laptop worker polls the public API over outbound HTTPS and runs Docker. Report runner-offline status accurately.
- Show the whole CRM path: request → generate → test → capped repair → reviewer activation → run → saved follow-up → rollback. Use one initial generation and at most two repairs.
- Use LiteLLM with OpenRouter. One sponsored generation task per invited account. Later tasks use a reviewer key held in session memory. Show daily app token use and cost. Allow free models only in the demo, including fallbacks.
- Keep reviewer keys out of persistence, logs, checkpoints, and generated-code containers. Run generated Python only in restricted Docker jobs. FastAPI validates all proposed CRM changes and activates immutable versions through a registry.
- Use Solar's color and visual direction. Confirm license coverage before reusing template files or assets. Measure the CRM workflow before making speed claims against Zoho.
- Keep the three phases and four-day maximum. Defer the advanced infrastructure listed in the plan.

## Working here

Run the smallest useful slice and verify through the actual entry point. Keep secrets in ignored local files and never stage them. Record tested commands, known limits, and the next task in the README when handing off. Ask for credentials through the IDE's secret handling or local environment setup. Do not put them in chat, Git, or portable archives.
