import os

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")
RUNNER_TOKEN = os.environ.get("RUNNER_TOKEN", "")
WORKER_ID = os.environ.get("WORKER_ID", "laptop-1")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
QA_IMAGE = os.environ.get("QA_IMAGE", "agentic-os-qa:latest")
RUNNER_FIXTURE = os.environ.get("RUNNER_FIXTURE", "") == "1"

POLL_SECONDS = float(os.environ.get("RUNNER_POLL_SECONDS", "3"))
HEARTBEAT_SECONDS = 10

MAX_GENERATION_ATTEMPTS = 3
MAX_PROVIDER_REQUESTS = 6
MODEL_TIMEOUT_SECONDS = 90
QA_TIMEOUT_SECONDS = 60
RUN_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 4000
MAX_RUN_TOKENS = 24000
MAX_DIAGNOSTIC_CHARS = 64 * 1024
MAX_BUNDLE_SOURCE = 64 * 1024

# Free-only model allowlist. Defaults are real ":free" catalog IDs fetched
# from https://openrouter.ai/api/v1/models on 2026-11-14; override with
# FREE_MODEL_ALLOWLIST. Paid models are never permitted in the demo.
FREE_MODEL_ALLOWLIST = {
    m.strip()
    for m in os.environ.get(
        "FREE_MODEL_ALLOWLIST",
        "nvidia/nemotron-3-ultra-550b-a55b:free,google/gemma-4-31b-it:free",
    ).split(",")
    if m.strip()
}
