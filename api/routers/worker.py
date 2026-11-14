"""Trusted worker endpoints. Authenticated by RUNNER_TOKEN bearer.
The worker polls outbound; the API never calls the laptop.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from .. import provider_keys, run_store
from ..deps import get_conn
from ..runner_auth import require_runner

router = APIRouter(prefix="/worker", tags=["worker"], dependencies=[Depends(require_runner)])

WORKER_ID_HEADER = "x-worker-id"


def _worker_id(request: Request) -> str:
    wid = request.headers.get(WORKER_ID_HEADER, "").strip()
    if not wid or len(wid) > 80:
        raise HTTPException(400, "Missing or invalid X-Worker-Id")
    return wid


@router.post("/claim")
def claim(request: Request, conn=Depends(get_conn)):
    job = run_store.claim_job(conn, _worker_id(request))
    if job is None:
        return {"job": None}
    if isinstance(job, dict) and job.get("busy"):
        return {"job": None, "note": "worker already has an active lease"}
    return {"job": job}


class HeartbeatRequest(BaseModel):
    lease_token: str = Field(min_length=10, max_length=200)


@router.post("/heartbeat")
def heartbeat(
    payload: HeartbeatRequest,
    request: Request,
    conn=Depends(get_conn),
):
    ok = run_store.heartbeat(conn, payload.lease_token, _worker_id(request))
    if not ok:
        raise HTTPException(409, "Lease expired or unknown")
    return {"ok": True}


class ProgressRequest(BaseModel):
    lease_token: str = Field(min_length=10, max_length=200)
    kind: str = Field(min_length=1, max_length=40)
    payload: dict = Field(default_factory=dict)


@router.post("/progress")
def progress(
    payload: ProgressRequest,
    request: Request,
    conn=Depends(get_conn),
):
    run_store.submit_progress(conn, payload.lease_token, _worker_id(request), payload.kind, payload.payload)
    return {"ok": True}


class ResultRequest(BaseModel):
    lease_token: str = Field(min_length=10, max_length=200)
    result: dict


@router.post("/result")
def result(
    payload: ResultRequest,
    request: Request,
    conn=Depends(get_conn),
):
    run_store.submit_result(conn, payload.lease_token, _worker_id(request), payload.result)
    return {"ok": True}


@router.get("/credentials/{ref}")
def credential(ref: str, request: Request, conn=Depends(get_conn)):
    """Return reviewer key material to the leased worker only.

    The ref must be unexpired, belong to the run's owner, and the caller's
    lease must be active on that run. The key is deleted after retrieval
    is attempted? No — it may be needed across repair attempts within the
    same job, so it stays until TTL/logout; it is never written anywhere.
    """
    worker_id = _worker_id(request)
    entry = provider_keys.get(ref)
    if not entry:
        raise HTTPException(404, "Unknown or expired credential reference")
    # Authorize: the requesting worker must hold an active lease on a run
    # owned by this user that references this credential.
    token_hash = None
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT r.id FROM provider_key_refs p
               JOIN runs r ON r.user_id = p.user_id
               JOIN job_leases l ON l.run_id = r.id
               WHERE p.ref = %s AND l.worker_id = %s
                 AND l.released_at IS NULL AND l.expires_at > now()
                 AND p.expires_at > now()
               LIMIT 1""",
            (ref, worker_id),
        )
        if not cur.fetchone():
            raise HTTPException(403, "Credential not available to this worker")
    return {"api_key": entry.key, "model_id": None}
