from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import deps, run_store
from ..deps import CurrentUser, get_conn, require_password_changed

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(deps.check_origin)])

CredentialMode = Literal["sponsored", "byok"]


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    credential_mode: CredentialMode = "sponsored"
    model_id: str | None = Field(default=None, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=128)


class CreateRunResponse(BaseModel):
    run_id: UUID
    status: str
    deduplicated: bool = False


@router.post("", response_model=CreateRunResponse, status_code=202)
def create_run(
    payload: CreateRunRequest,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    if payload.credential_mode == "byok":
        # Verify a live reviewer key exists before accepting the run.
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM provider_key_refs WHERE user_id = %s AND expires_at > now() LIMIT 1",
                (user.id,),
            )
            if not cur.fetchone():
                raise HTTPException(409, "No reviewer key attached for this session")
    run_id, created = run_store.create_run(
        conn,
        workspace_id=user.workspace_id,
        user_id=user.id,
        kind="generate",
        credential_mode=payload.credential_mode,
        prompt=payload.prompt,
        model_id=payload.model_id,
        idempotency_key=payload.idempotency_key,
    )
    return CreateRunResponse(run_id=run_id, status="queued", deduplicated=not created)


@router.get("")
def list_runs(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    items = run_store.list_runs(conn, user.id, limit, offset)
    return {"items": items, "limit": limit, "offset": offset}


@router.get("/{run_id}")
def get_run(
    run_id: UUID,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    return run_store.get_run_for_user(conn, user.id, run_id)


@router.get("/{run_id}/events")
def get_events(
    run_id: UUID,
    after: int = Query(0, ge=0),
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    run = run_store.get_run_for_user(conn, user.id, run_id)
    return {"run_id": str(run_id), "events": [e for e in run["events"] if e["seq"] > after]}


@router.post("/{run_id}/cancel")
def cancel_run(
    run_id: UUID,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    run_store.cancel_run(conn, user.id, run_id)
    return {"status": "cancelled"}
