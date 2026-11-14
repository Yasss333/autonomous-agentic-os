"""Session-memory provider key attachment (BYOK).

The key travels over HTTPS once, lives in API process memory under an
opaque ref, and is fetchable only by the currently leased trusted worker.
It is never persisted, logged, or placed in job payloads.
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from .. import config, deps, provider_keys, run_store
from ..deps import CurrentUser, get_conn

router = APIRouter(prefix="/session", tags=["session"])


class ProviderKeyRequest(BaseModel):
    api_key: str = Field(min_length=10, max_length=500)
    model_id: str | None = Field(default=None, max_length=120)


def _insert_ref(conn, user_id, ref: str) -> None:
    expires = datetime.now(UTC) + timedelta(seconds=config.PROVIDER_KEY_TTL_SECONDS)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO provider_key_refs (ref, user_id, expires_at) VALUES (%s, %s, %s)",
            (ref, user_id, expires),
        )


@router.post("/provider-key")
def attach_key(
    payload: ProviderKeyRequest,
    request: Request,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    deps.check_origin(request)
    deps.require_password_changed(user)
    # OpenRouter keys start with "sk-or-"; reject obvious junk early.
    if not payload.api_key.startswith("sk-"):
        raise HTTPException(422, "That does not look like an OpenRouter API key")
    ref = provider_keys.put(str(user.id), payload.api_key)
    _insert_ref(conn, user.id, ref)
    return {
        "status": "attached",
        "expires_in_seconds": config.PROVIDER_KEY_TTL_SECONDS,
        "model_id": payload.model_id,
    }


@router.delete("/provider-key")
def detach_key(
    request: Request,
    response: Response,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    deps.check_origin(request)
    removed = provider_keys.remove_for_user(str(user.id))
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE provider_key_refs SET expires_at = now() WHERE user_id = %s",
            (user.id,),
        )
    return {"status": "detached", "cleared_refs": removed}


@router.get("/provider-key")
def key_status(
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT count(*) AS n FROM provider_key_refs WHERE user_id = %s AND expires_at > now()",
            (user.id,),
        )
        n = cur.fetchone()["n"]
    return {"attached": n > 0, "refs": n}
