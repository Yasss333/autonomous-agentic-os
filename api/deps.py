import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response
from psycopg.rows import dict_row

from . import config, db, security
from .schemas import MeResponse


@dataclass
class CurrentUser:
    id: UUID
    email: str
    workspace_id: UUID
    workspace_slug: str
    must_change_password: bool
    sponsored_task_used: bool


def get_conn(request: Request):
    if not db.database_configured():
        raise HTTPException(503, "Database is not configured. Set DATABASE_URL.")
    pool = db.get_pool()
    with pool.connection() as conn:
        yield conn


def check_origin(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if not origin:
        return
    host = urlparse(origin).netloc.lower()
    allowed = {request.headers.get("host", "").lower()} | {
        urlparse(o).netloc.lower() for o in config.ALLOWED_ORIGINS
    }
    if host not in allowed:
        # Development: any localhost/loopback origin is fine (covers the IDE
        # browser preview proxy, which uses a different port than Vite).
        if config.APP_ENV == "development" and (
            host.startswith("localhost") or host.startswith("127.0.0.1") or host.startswith("[::1]")
        ):
            return
        raise HTTPException(403, "Cross-origin request rejected")


_login_attempts: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_LOGIN_WINDOW = 600
_LOGIN_MAX = 5


def _throttle_key(request: Request, email: str) -> tuple[str, str]:
    ip = request.client.host if request.client else "unknown"
    return (email.lower(), ip)


def check_login_throttle(request: Request, email: str) -> None:
    key = _throttle_key(request, email)
    now = time.monotonic()
    attempts = _login_attempts[key]
    while attempts and now - attempts[0] > _LOGIN_WINDOW:
        attempts.popleft()
    if len(attempts) >= _LOGIN_MAX:
        raise HTTPException(429, "Too many login attempts. Try again later.")


def record_login_failure(request: Request, email: str) -> None:
    _login_attempts[_throttle_key(request, email)].append(time.monotonic())


def clear_login_failures(request: Request, email: str) -> None:
    _login_attempts.pop(_throttle_key(request, email), None)


async def current_user(
    request: Request, response: Response, conn=Depends(get_conn)
) -> CurrentUser:
    token = request.cookies.get(security.SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "Not signed in")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT u.id, u.email, u.workspace_id, u.must_change_password,
                   w.slug AS workspace_slug,
                   EXISTS (
                     SELECT 1 FROM demo_allowances d
                     WHERE d.user_id = u.id AND d.sponsored_used_at IS NOT NULL
                   ) AS sponsored_task_used
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            JOIN workspaces w ON w.id = u.workspace_id
            WHERE s.token_hash = %s
              AND s.revoked_at IS NULL
              AND s.expires_at > now()
              AND u.status = 'active'
            """,
            (security.token_digest(token),),
        )
        row = cur.fetchone()
    if not row:
        response.delete_cookie(security.SESSION_COOKIE, path="/")
        raise HTTPException(401, "Session expired or invalid")
    return CurrentUser(**row)


def require_password_changed(user: CurrentUser) -> None:
    if user.must_change_password:
        raise HTTPException(403, "Password change required", headers={"X-Code": "password_change_required"})


def me_response(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        workspace_id=user.workspace_id,
        workspace_slug=user.workspace_slug,
        must_change_password=user.must_change_password,
        sponsored_task_used=user.sponsored_task_used,
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
