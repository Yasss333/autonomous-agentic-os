import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash

from . import config

password_hash = PasswordHash.recommended()

SESSION_COOKIE = "aos_session"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password_hash_str: str, password: str) -> bool:
    try:
        return password_hash.verify(password, password_hash_str)
    except Exception:
        return False


def new_session_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def session_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=config.SESSION_TTL_SECONDS)


def cookie_kwargs() -> dict:
    return {
        "key": SESSION_COOKIE,
        "httponly": True,
        "samesite": "lax",
        "secure": config.SESSION_COOKIE_SECURE,
        "path": "/",
        "max_age": config.SESSION_TTL_SECONDS,
    }
