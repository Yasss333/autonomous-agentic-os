import hashlib
import hmac

from fastapi import Depends, HTTPException, Request

from . import config


def _expected_hash() -> str:
    return hashlib.sha256(config.RUNNER_TOKEN.encode()).hexdigest()


def require_runner(request: Request) -> None:
    if not config.RUNNER_TOKEN:
        raise HTTPException(503, "Runner is not configured on the server")
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.lower().startswith("bearer ") else ""
    if not token or not hmac.compare_digest(
        hashlib.sha256(token.encode()).hexdigest(), _expected_hash()
    ):
        raise HTTPException(401, "Invalid runner credential")
