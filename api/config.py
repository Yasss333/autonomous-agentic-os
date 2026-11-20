import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
for candidate in (ROOT / ".env", ROOT / "api" / ".env"):
    if candidate.exists():
        load_dotenv(candidate)
        break


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"} or (
        default and os.environ.get(name, "").lower() not in {"0", "false", "no", "off"}
    )


DATABASE_URL = os.environ.get("DATABASE_URL", "")
DATABASE_DIRECT_URL = os.environ.get("DATABASE_DIRECT_URL", "") or DATABASE_URL

APP_ENV = os.environ.get("APP_ENV", "development")
LOCAL_DEMO = APP_ENV == "development" and os.environ.get("LOCAL_DEMO", "") == "1"
CLERK_ISSUER = os.environ.get("CLERK_ISSUER", "").strip().rstrip("/")
CLERK_AUTHORIZED_PARTIES = {
    origin.strip() for origin in os.environ.get("CLERK_AUTHORIZED_PARTIES", "").split(",")
    if origin.strip()
}
SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", APP_ENV == "production")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", str(7 * 24 * 3600)))
ALLOWED_ORIGINS = {
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
}
SEED_WORKSPACE_SLUG = os.environ.get("SEED_WORKSPACE_SLUG", "demo")

# Phase 2
RUNNER_TOKEN = os.environ.get("RUNNER_TOKEN", "")
STUDIO_OPENROUTER_API_KEY = os.environ.get("STUDIO_OPENROUTER_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
# Comma-separated catalog IDs the demo may use; paid models are never allowed.
FREE_MODEL_ALLOWLIST = {
    m.strip() for m in os.environ.get("FREE_MODEL_ALLOWLIST", "").split(",") if m.strip()
}
PROVIDER_KEY_TTL_SECONDS = int(os.environ.get("PROVIDER_KEY_TTL_SECONDS", "1800"))
# Run limits from the plan (initial configuration values).
MAX_GENERATION_ATTEMPTS = 3
MAX_PROVIDER_REQUESTS = 6
MODEL_TIMEOUT_SECONDS = 90
QA_TIMEOUT_SECONDS = 60
RUN_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 4000
MAX_RUN_TOKENS = 24000
MAX_DIAGNOSTIC_CHARS = 64 * 1024
MAX_TOOL_OPERATIONS = 50
