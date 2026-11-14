"""Trusted laptop worker.

Polls the public API outbound for jobs, runs the LangGraph generate/QA
flow or isolated tool invocations in Docker, and submits results back.
Holds the owner's sponsored OpenRouter key from its own environment;
reviewer BYOK keys are fetched per-job over the authenticated channel and
kept only in memory.

Run:  python -m runner.worker
Env:  API_BASE_URL, RUNNER_TOKEN, WORKER_ID, OPENROUTER_API_KEY (sponsored),
      QA_IMAGE, RUNNER_FIXTURE=1 for the labeled test-fixture generator.
"""
