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
SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", APP_ENV == "production")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", str(7 * 24 * 3600)))
ALLOWED_ORIGINS = {
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
}
SEED_WORKSPACE_SLUG = os.environ.get("SEED_WORKSPACE_SLUG", "demo")
