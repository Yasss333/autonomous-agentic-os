"""Validation and atomic commit of operations proposed by generated tools.

Generated code never touches the database. It returns JSON operations;
FastAPI validates each against the workspace's current data and commits
them in the run's transaction. Unknown ops, cross-workspace references,
and oversized batches are rejected.
"""

from uuid import UUID

from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import config, crm_store
from .schemas import ActivityCreate, LeadUpdate, TaskCreate

ALLOWED_OPS = {"create_followup_task", "add_activity", "update_lead_stage"}


def _lead_version(cur, workspace_id: UUID, lead_id: UUID) -> int:
    cur.execute(
        "SELECT version FROM entity_nodes WHERE id = %s AND workspace_id = %s AND type = 'lead'",
        (lead_id, workspace_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(400, f"Operation references unknown lead {lead_id}")
    return row["version"]


def commit_operations(conn, workspace_id: UUID, operations: list) -> dict:
    """Validate and commit proposed CRM writes. Returns a summary."""
    if not isinstance(operations, list):
        raise HTTPException(422, "operations must be a list")
    if len(operations) > config.MAX_TOOL_OPERATIONS:
        raise HTTPException(422, f"Too many operations (max {config.MAX_TOOL_OPERATIONS})")

    applied = []
    seen_keys = set()
    for op in operations:
        if not isinstance(op, dict):
            raise HTTPException(422, "Each operation must be an object")
        name = op.get("op")
        if name not in ALLOWED_OPS:
            raise HTTPException(422, f"Operation '{name}' is not allowed")
        op_key = op.get("op_key")
        if op_key:
            if op_key in seen_keys:
                continue  # duplicate proposal in same batch: skip, don't double-apply
            seen_keys.add(op_key)

        if name == "create_followup_task":
            payload = TaskCreate(
                title=op.get("title", ""),
                due_date=op.get("due_date"),
                lead_id=UUID(op["lead_id"]) if op.get("lead_id") else None,
                status="open",
            )
            task = crm_store.create_task(conn, workspace_id, payload)
            applied.append({"op": name, "id": str(task.id)})

        elif name == "add_activity":
            payload = ActivityCreate(
                kind=op.get("kind", "note"),
                body=op.get("body", ""),
            )
            lead_id = UUID(op["lead_id"])
            activity = crm_store.add_activity(conn, workspace_id, lead_id, payload)
            applied.append({"op": name, "id": str(activity.id)})

        elif name == "update_lead_stage":
            lead_id = UUID(op["lead_id"])
            with conn.cursor(row_factory=dict_row) as cur:
                version = _lead_version(cur, workspace_id, lead_id)
            payload = LeadUpdate(version=version, stage=op.get("stage"))
            crm_store.update_lead(conn, workspace_id, lead_id, payload)
            applied.append({"op": name, "lead_id": str(lead_id)})

    return {"applied": applied, "count": len(applied)}
