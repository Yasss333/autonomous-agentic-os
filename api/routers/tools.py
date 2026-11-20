"""Tool registry: listing, activation, rollback, invocation, usage."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from .. import deps, run_store
from ..deps import CurrentUser, get_conn, require_password_changed

router = APIRouter(prefix="/tools", tags=["tools"], dependencies=[Depends(deps.check_origin)])


class ActivateRequest(BaseModel):
    version: int = Field(ge=1)
    expected_active_version_id: UUID | None = None


class RollbackRequest(BaseModel):
    target_version: int | None = Field(default=None, ge=1)


class InvokeRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=128)


def _registry_row(cur, workspace_id: UUID, name: str):
    cur.execute(
        "SELECT * FROM tool_registry WHERE workspace_id = %s AND name = %s",
        (workspace_id, name),
    )
    return cur.fetchone()


@router.get("")
def list_tools(
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT r.name, r.active_version_id, r.updated_at,
                      tv.version AS active_version, tv.status AS active_status,
                      tv.source_hash, tv.qa_result
               FROM tool_registry r
               LEFT JOIN tool_versions tv ON tv.id = r.active_version_id
               WHERE r.workspace_id = %s
               ORDER BY r.name""",
            (user.workspace_id,),
        )
        tools = cur.fetchall()
        cur.execute(
            """SELECT id, name, version, status, source_hash, created_at
               FROM tool_versions WHERE workspace_id = %s
               ORDER BY name, version DESC""",
            (user.workspace_id,),
        )
        versions = cur.fetchall()
    return {"tools": tools, "versions": versions}


@router.get("/{name}")
def get_tool(
    name: str,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT id, name, version, schema_version, source_hash, ui_spec,
                      input_schema, output_schema, qa_result, status, created_at
               FROM tool_versions
               WHERE workspace_id = %s AND name = %s
               ORDER BY version DESC""",
            (user.workspace_id, name),
        )
        versions = cur.fetchall()
        reg = _registry_row(cur, user.workspace_id, name)
    if not versions and not reg:
        raise HTTPException(404, "Tool not found")
    return {
        "name": name,
        "active_version_id": str(reg["active_version_id"]) if reg and reg["active_version_id"] else None,
        "versions": versions,
    }


@router.post("/{name}/activate")
def activate(
    name: str,
    payload: ActivateRequest,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT id, version, status, source_hash FROM tool_versions
               WHERE workspace_id = %s AND name = %s AND version = %s""",
            (user.workspace_id, name, payload.version),
        )
        target = cur.fetchone()
        if not target:
            raise HTTPException(404, "Tool version not found")
        if target["status"] != "passed":
            raise HTTPException(409, "Only QA-passed versions can be activated")
        reg = _registry_row(cur, user.workspace_id, name)
        current = reg["active_version_id"] if reg else None
        if payload.expected_active_version_id is not None and current != payload.expected_active_version_id:
            raise HTTPException(409, "Active version changed; reload and retry")
        cur.execute(
            """INSERT INTO tool_registry (workspace_id, name, active_version_id, updated_at)
               VALUES (%s, %s, %s, now())
               ON CONFLICT (workspace_id, name)
               DO UPDATE SET active_version_id = EXCLUDED.active_version_id, updated_at = now()""",
            (user.workspace_id, name, target["id"]),
        )
        # Audit event on a synthetic run? Use run_events only for runs; record
        # activation via a dedicated event row is overkill — the registry row
        # plus version timestamps are the audit trail for v1.
    return {"status": "active", "version": target["version"], "source_hash": target["source_hash"]}


@router.post("/{name}/rollback")
def rollback(
    name: str,
    payload: RollbackRequest,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    with conn.cursor(row_factory=dict_row) as cur:
        reg = _registry_row(cur, user.workspace_id, name)
        if not reg or not reg["active_version_id"]:
            raise HTTPException(404, "No active version to roll back")
        cur.execute(
            """SELECT id, version FROM tool_versions
               WHERE workspace_id = %s AND name = %s AND status = 'passed'
                 AND ((%s::integer IS NOT NULL AND version = %s) OR
                      (%s::integer IS NULL AND version < (SELECT version FROM tool_versions WHERE id = %s)))
               ORDER BY version DESC LIMIT 1""",
            (user.workspace_id, name, payload.target_version, payload.target_version, payload.target_version, reg["active_version_id"]),
        )
        candidates = cur.fetchall()
        if payload.target_version is not None:
            target = next((c for c in candidates if c["version"] == payload.target_version), None)
            if not target:
                raise HTTPException(404, "Target version not found or not QA-passed")
        else:
            target = candidates[0] if candidates else None
        if not target:
            raise HTTPException(409, "No previous passing version to roll back to")
        cur.execute(
            "UPDATE tool_registry SET active_version_id = %s, updated_at = now() "
            "WHERE workspace_id = %s AND name = %s",
            (target["id"], user.workspace_id, name),
        )
    return {"status": "rolled_back", "version": target["version"]}


@router.post("/{name}/invoke", status_code=202)
def invoke(
    name: str,
    payload: InvokeRequest,
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    with conn.cursor(row_factory=dict_row) as cur:
        reg = _registry_row(cur, user.workspace_id, name)
        if not reg or not reg["active_version_id"]:
            raise HTTPException(409, "Tool has no active version")
        cur.execute(
            "SELECT version, status, input_schema FROM tool_versions WHERE id = %s",
            (reg["active_version_id"],),
        )
        tv = cur.fetchone()
        if not tv or tv["status"] != "passed":
            raise HTTPException(409, "Active version is not QA-passed")

        from jsonschema import Draft202012Validator
        errors = list(Draft202012Validator(tv["input_schema"]).iter_errors(payload.input))
        if errors:
            raise HTTPException(422, "Tool input does not match the generated form: " + errors[0].message[:200])

        # Business idempotency: one effect per (workspace, key).
        cur.execute(
            "SELECT run_id FROM invocation_keys WHERE workspace_id = %s AND idem_key = %s",
            (user.workspace_id, payload.idempotency_key),
        )
        existing = cur.fetchone()
        if existing:
            return {"run_id": str(existing["run_id"]), "status": "deduplicated"}

        if not run_store.runner_online(conn):
            raise HTTPException(503, "Runner is offline. Start the worker and retry.")

        run_id, _ = run_store.create_run(
            conn,
            workspace_id=user.workspace_id,
            user_id=user.id,
            kind="tool_invoke",
            credential_mode="none",
            input_data={"tool_input": payload.input, "tool_name": name},
            tool_version_id=reg["active_version_id"],
            idempotency_key=f"invoke:{payload.idempotency_key}",
        )
        cur.execute(
            "INSERT INTO invocation_keys (workspace_id, idem_key, run_id) VALUES (%s, %s, %s)",
            (user.workspace_id, payload.idempotency_key, run_id),
        )
    return {"run_id": str(run_id), "status": "queued"}


@router.get("/usage/today")
def usage_today(
    user: CurrentUser = Depends(deps.current_user),
    conn=Depends(get_conn),
):
    require_password_changed(user)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT model_id, payer,
                      COALESCE(SUM(input_tokens), 0) AS input_tokens,
                      COALESCE(SUM(output_tokens), 0) AS output_tokens,
                      SUM(cost_usd) AS cost_usd,
                      bool_and(cost_known) AS all_cost_known,
                      count(*) AS calls
               FROM usage_events
               WHERE workspace_id = %s
                 AND created_at >= (now() AT TIME ZONE 'Asia/Kolkata')::date
                                AT TIME ZONE 'Asia/Kolkata'
               GROUP BY model_id, payer
               ORDER BY model_id""",
            (user.workspace_id,),
        )
        rows = cur.fetchall()
    return {
        "day": "Asia/Kolkata",
        "items": [
            {
                **r,
                "cost_usd": float(r["cost_usd"]) if r["cost_usd"] is not None else None,
                "all_cost_known": bool(r["all_cost_known"]),
            }
            for r in rows
        ],
    }
