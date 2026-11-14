"""Run lifecycle: creation with allowance reservation, worker leases,
events, results, and cancellation. All functions take an open connection.
"""

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import config

RUN_STATUSES = {
    "queued", "needs_key", "generating", "testing", "repairing",
    "awaiting_activation", "succeeded", "failed", "cancelled",
}
TERMINAL = {"succeeded", "failed", "cancelled"}


def _now() -> datetime:
    return datetime.now(UTC)


def _event(cur, run_id: UUID, kind: str, payload: dict | None = None) -> int:
    cur.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM run_events WHERE run_id = %s",
        (run_id,),
    )
    seq = cur.fetchone()["seq"]
    cur.execute(
        "INSERT INTO run_events (run_id, seq, kind, payload) VALUES (%s, %s, %s, %s)",
        (run_id, seq, kind, Jsonb(payload or {})),
    )
    return seq


def set_status(conn, run_id: UUID, status: str, fields: dict | None = None) -> None:
    assert status in RUN_STATUSES, status
    cols = {"status": status, "updated_at": _now()}
    safe = {
        k: v for k, v in (fields or {}).items()
        if k in {"error_code", "artifact_hash", "tool_version_id", "attempt_count", "bundle"}
    }
    cols.update(safe)
    assignments = ", ".join(f"{k} = %s" for k in cols)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE runs SET {assignments} WHERE id = %s",
            (*cols.values(), run_id),
        )
        _event(cur, run_id, "status", {"status": status, **{
            k: v for k, v in safe.items() if isinstance(v, (str, int, bool)) or v is None
        }})


def runner_online(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM workers WHERE last_seen > now() - interval '90 seconds' LIMIT 1"
        )
        return cur.fetchone() is not None


def create_run(
    conn,
    *,
    workspace_id: UUID,
    user_id: UUID,
    kind: str,
    credential_mode: str,
    prompt: str | None = None,
    model_id: str | None = None,
    input_data: dict | None = None,
    tool_version_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> tuple[UUID, bool]:
    """Returns (run_id, created). Idempotent on (user_id, idempotency_key).

    Sponsored allowance is reserved in the same transaction, only when a
    runner is online. Reviewer-key (byok) runs do not consume it.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        if idempotency_key:
            cur.execute(
                "SELECT id, kind FROM runs WHERE user_id = %s AND idempotency_key = %s",
                (user_id, idempotency_key),
            )
            existing = cur.fetchone()
            if existing:
                return existing["id"], False

        if kind == "generate" and credential_mode == "sponsored":
            # One sponsored generation run per account, ever (demo).
            cur.execute(
                "SELECT sponsored_used_at FROM demo_allowances WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            allowance = cur.fetchone()
            if not allowance or allowance["sponsored_used_at"] is not None:
                raise HTTPException(
                    402, "Sponsored task already used. Attach your OpenRouter key to continue.",
                )
            if not runner_online(conn):
                raise HTTPException(503, "Runner is offline. Start the worker and retry.")
            cur.execute(
                "UPDATE demo_allowances SET sponsored_used_at = now(), updated_at = now() WHERE user_id = %s",
                (user_id,),
            )

        cur.execute(
            """INSERT INTO runs (workspace_id, user_id, kind, status, prompt, credential_mode,
                                model_id, input, tool_version_id, idempotency_key)
               VALUES (%s, %s, %s, 'queued', %s, %s, %s, %s, %s, %s) RETURNING id""",
            (
                workspace_id, user_id, kind, prompt, credential_mode, model_id,
                Jsonb(input_data) if input_data is not None else None,
                tool_version_id, idempotency_key,
            ),
        )
        run_id = cur.fetchone()["id"]
        _event(cur, run_id, "created", {"kind": kind, "credential_mode": credential_mode})
        return run_id, True


def claim_job(conn, worker_id: str):
    """Lease the oldest queued job for this worker. Returns job payload or None."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "INSERT INTO workers (worker_id, last_seen) VALUES (%s, now()) "
            "ON CONFLICT (worker_id) DO UPDATE SET last_seen = now()",
            (worker_id,),
        )
        cur.execute(
            """SELECT id, kind, status, prompt, credential_mode, model_id, input,
                      tool_version_id, workspace_id, user_id, attempt_count
               FROM runs
               WHERE status = 'queued'
               ORDER BY created_at
               LIMIT 1
               FOR UPDATE SKIP LOCKED""",
        )
        run = cur.fetchone()
        if not run:
            return None

        # Expire stale leases so a crashed worker's job can be reclaimed.
        cur.execute(
            """UPDATE job_leases SET released_at = now()
               WHERE released_at IS NULL AND expires_at < now()""",
        )
        cur.execute(
            """SELECT 1 FROM job_leases WHERE run_id = %s AND released_at IS NULL""",
            (run["id"],),
        )
        if cur.fetchone():
            return {"busy": True}

        lease_token = secrets.token_urlsafe(32)
        expires = _now() + timedelta(seconds=30)
        cur.execute(
            """INSERT INTO job_leases (run_id, worker_id, lease_token, expires_at)
               VALUES (%s, %s, %s, %s)""",
            (run["id"], worker_id, hashlib.sha256(lease_token.encode()).hexdigest(), expires),
        )
        new_status = "generating" if run["kind"] == "generate" else "testing"
        cur.execute(
            "UPDATE runs SET status = %s, updated_at = now() WHERE id = %s",
            (new_status, run["id"]),
        )
        _event(cur, run["id"], "claimed", {"worker_id": worker_id, "kind": run["kind"]})

        # Resolve credential reference for BYOK runs (key stays in API memory).
        credential_ref = None
        if run["credential_mode"] == "byok":
            cur.execute(
                """SELECT ref FROM provider_key_refs
                   WHERE user_id = %s AND expires_at > now()
                   ORDER BY created_at DESC LIMIT 1""",
                (run["user_id"],),
            )
            ref_row = cur.fetchone()
            credential_ref = ref_row["ref"] if ref_row else None

        # Tool invocations carry the pinned source and a bounded CRM snapshot.
        tool_payload = None
        if run["kind"] == "tool_invoke" and run["tool_version_id"]:
            cur.execute(
                """SELECT id, name, version, source_code, source_hash, input_schema,
                          ui_spec, output_schema
                   FROM tool_versions WHERE id = %s""",
                (run["tool_version_id"],),
            )
            tv = cur.fetchone()
            if tv:
                tool_payload = {
                    "tool_version_id": str(tv["id"]),
                    "name": tv["name"],
                    "version": tv["version"],
                    "source_hash": tv["source_hash"],
                    "source_code": tv["source_code"],
                    "input_schema": tv["input_schema"],
                    "ui_spec": tv["ui_spec"],
                    "output_schema": tv["output_schema"],
                    "input": run["input"],
                    "snapshot": crm_snapshot(cur, run["workspace_id"]),
                }

        return {
            "run_id": str(run["id"]),
            "kind": run["kind"],
            "status": new_status,
            "prompt": run["prompt"],
            "model_id": run["model_id"],
            "credential_mode": run["credential_mode"],
            "credential_ref": credential_ref,
            "input": run["input"],
            "tool": tool_payload,
            "attempt_count": run["attempt_count"],
            "lease": {
                "token": lease_token,
                "expires_at": expires.isoformat(),
            },
            "limits": {
                "max_attempts": config.MAX_GENERATION_ATTEMPTS,
                "max_provider_requests": config.MAX_PROVIDER_REQUESTS,
                "model_timeout": config.MODEL_TIMEOUT_SECONDS,
                "qa_timeout": config.QA_TIMEOUT_SECONDS,
                "max_output_tokens": config.MAX_OUTPUT_TOKENS,
                "max_run_tokens": config.MAX_RUN_TOKENS,
                "max_diagnostic_chars": config.MAX_DIAGNOSTIC_CHARS,
            },
        }


def crm_snapshot(cur, workspace_id: UUID, limit: int = 200) -> dict:
    """Bounded read-only CRM snapshot handed to generated tools."""
    out = {"leads": [], "companies": [], "tasks": []}
    cur.execute(
        """SELECT n.id, n.name, t.data FROM entity_nodes n
           JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'lead'
           WHERE n.workspace_id = %s AND n.type = 'lead'
           ORDER BY n.updated_at DESC LIMIT %s""",
        (workspace_id, limit),
    )
    out["leads"] = [
        {"id": str(r["id"]), "name": r["name"], **(r["data"] or {})}
        for r in cur.fetchall()
    ]
    cur.execute(
        """SELECT n.id, n.name, t.data FROM entity_nodes n
           JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'company'
           WHERE n.workspace_id = %s AND n.type = 'company'
           ORDER BY n.name LIMIT %s""",
        (workspace_id, limit),
    )
    out["companies"] = [
        {"id": str(r["id"]), "name": r["name"], **(r["data"] or {})}
        for r in cur.fetchall()
    ]
    cur.execute(
        """SELECT n.id, n.name, t.data FROM entity_nodes n
           JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'task'
           WHERE n.workspace_id = %s AND n.type = 'task'
           ORDER BY n.updated_at DESC LIMIT %s""",
        (workspace_id, limit),
    )
    out["tasks"] = [
        {"id": str(r["id"]), "name": r["name"], **(r["data"] or {})}
        for r in cur.fetchall()
    ]
    return out


def heartbeat(conn, lease_token: str, worker_id: str) -> bool:
    token_hash = hashlib.sha256(lease_token.encode()).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE job_leases
               SET expires_at = now() + interval '30 seconds'
               WHERE lease_token = %s AND worker_id = %s
                 AND released_at IS NULL AND expires_at > now()""",
            (token_hash, worker_id),
        )
        ok = cur.rowcount == 1
        if ok:
            cur.execute(
                "UPDATE workers SET last_seen = now() WHERE worker_id = %s", (worker_id,)
            )
        return ok


def _lease_run(conn, lease_token: str, worker_id: str):
    token_hash = hashlib.sha256(lease_token.encode()).hexdigest()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT l.id AS lease_id, l.run_id, l.generation, r.status, r.kind,
                      r.workspace_id, r.user_id, r.attempt_count
               FROM job_leases l JOIN runs r ON r.id = l.run_id
               WHERE l.lease_token = %s AND l.worker_id = %s
                 AND l.released_at IS NULL AND l.expires_at > now()""",
            (token_hash, worker_id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(409, "Lease expired or unknown; result rejected")
    return row


def submit_progress(conn, lease_token: str, worker_id: str, kind: str, payload: dict):
    lease = _lease_run(conn, lease_token, worker_id)
    if lease["status"] in TERMINAL:
        raise HTTPException(409, "Run already finished")
    status_map = {
        "generating": "generating",
        "testing": "testing",
        "repairing": "repairing",
        "needs_key": "needs_key",
    }
    new_status = status_map.get(kind)
    with conn.cursor() as cur:
        if new_status:
            cur.execute(
                "UPDATE runs SET status = %s, updated_at = now() WHERE id = %s",
                (new_status, lease["run_id"]),
            )
        _event(cur, lease["run_id"], kind, payload)


def submit_result(conn, lease_token: str, worker_id: str, result: dict):
    """Final result for a leased job. Applies status, usage, artifacts."""
    lease = _lease_run(conn, lease_token, worker_id)
    run_id = lease["run_id"]
    outcome = result.get("outcome")
    if outcome not in {"succeeded", "failed", "awaiting_activation", "needs_key", "cancelled"}:
        raise HTTPException(422, "Unknown outcome")

    with conn.cursor(row_factory=dict_row) as cur:
        # Persist usage facts reported by the trusted worker.
        for u in result.get("usage", []) or []:
            cur.execute(
                """INSERT INTO usage_events
                   (workspace_id, user_id, run_id, model_id, payer,
                    input_tokens, output_tokens, cost_usd, cost_known)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    lease["workspace_id"], lease["user_id"], run_id,
                    u.get("model_id", "unknown"), u.get("payer", "unknown"),
                    u.get("input_tokens"), u.get("output_tokens"),
                    u.get("cost_usd"), bool(u.get("cost_known")),
                ),
            )

        tool_version_id = None
        if outcome == "awaiting_activation" and lease["kind"] == "generate":
            bundle = result.get("bundle") or {}
            source = bundle.get("source_code", "")
            if not source or len(source.encode()) > 128 * 1024:
                raise HTTPException(422, "Missing or oversized tool source")
            source_hash = hashlib.sha256(source.encode()).hexdigest()
            cur.execute(
                """SELECT id, version FROM tool_versions
                   WHERE workspace_id = %s AND name = %s
                   ORDER BY version DESC LIMIT 1""",
                (lease["workspace_id"], bundle.get("name", "tool")),
            )
            last = cur.fetchone()
            version = (last["version"] + 1) if last else 1
            cur.execute(
                """INSERT INTO tool_versions
                   (workspace_id, name, version, schema_version, source_hash,
                    source_code, ui_spec, input_schema, output_schema, qa_result, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'passed')
                   RETURNING id""",
                (
                    lease["workspace_id"], bundle["name"], version,
                    bundle.get("schema_version", 1), source_hash, source,
                    Jsonb(bundle.get("ui_spec") or {}),
                    Jsonb(bundle.get("input_schema") or {}),
                    Jsonb(bundle.get("output_schema") or {}),
                    Jsonb(result.get("qa") or {}),
                ),
            )
            tool_version_id = cur.fetchone()["id"]
            cur.execute(
                "UPDATE runs SET bundle = %s, artifact_hash = %s, tool_version_id = %s WHERE id = %s",
                (Jsonb(bundle), source_hash, tool_version_id, run_id),
            )
        elif outcome == "succeeded" and lease["kind"] == "tool_invoke":
            # Validate and commit proposed CRM writes in this same transaction.
            from . import tool_ops

            ops_result = tool_ops.commit_operations(
                conn, lease["workspace_id"], result.get("operations") or []
            )
            cur.execute(
                "UPDATE runs SET bundle = %s WHERE id = %s",
                (
                    Jsonb({
                        "display": result.get("display") or {},
                        "operations_result": ops_result,
                    }),
                    run_id,
                ),
            )

        # Proven pre-provider failure (needs_key with zero usage) refunds the
        # sponsored allowance. Ambiguous timeouts are never auto-refunded.
        if (
            outcome == "needs_key"
            and lease["kind"] == "generate"
            and not result.get("usage")
        ):
            cur.execute(
                """UPDATE demo_allowances SET sponsored_used_at = NULL, updated_at = now()
                   WHERE user_id = %s""",
                (lease["user_id"],),
            )
            _event(cur, run_id, "allowance_refunded", {})

        error_code = result.get("error_code")
        fields = {"status": outcome, "updated_at": _now()}
        if isinstance(result.get("attempts"), int):
            fields["attempt_count"] = result["attempts"]
        if tool_version_id:
            fields["tool_version_id"] = tool_version_id
        if error_code:
            fields["error_code"] = error_code
        if outcome == "awaiting_activation":
            fields["status"] = "awaiting_activation"
        assignments = ", ".join(f"{k} = %s" for k in fields)
        cur.execute(
            f"UPDATE runs SET {assignments} WHERE id = %s",
            (*fields.values(), run_id),
        )
        cur.execute(
            "UPDATE job_leases SET released_at = now() WHERE id = %s",
            (lease["lease_id"],),
        )
        _event(
            cur, run_id, "result",
            {
                "outcome": outcome,
                "error_code": error_code,
                "attempts": result.get("attempts"),
                "tool_version_id": str(tool_version_id) if tool_version_id else None,
            },
        )


def cancel_run(conn, user_id: UUID, run_id: UUID):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, status, user_id FROM runs WHERE id = %s AND user_id = %s FOR UPDATE",
            (run_id, user_id),
        )
        run = cur.fetchone()
        if not run:
            raise HTTPException(404, "Run not found")
        if run["status"] in TERMINAL:
            return
        cur.execute(
            "UPDATE runs SET status = 'cancelled', updated_at = now() WHERE id = %s",
            (run_id,),
        )
        cur.execute(
            "UPDATE job_leases SET released_at = now() WHERE run_id = %s AND released_at IS NULL",
            (run_id,),
        )
        _event(cur, run_id, "status", {"status": "cancelled"})


def get_run_for_user(conn, user_id: UUID, run_id: UUID):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT id, kind, status, prompt, credential_mode, model_id, attempt_count,
                      artifact_hash, error_code, tool_version_id, created_at, updated_at,
                      input, bundle
               FROM runs WHERE id = %s AND user_id = %s""",
            (run_id, user_id),
        )
        run = cur.fetchone()
        if not run:
            raise HTTPException(404, "Run not found")
        cur.execute(
            "SELECT seq, kind, payload, created_at FROM run_events WHERE run_id = %s ORDER BY seq",
            (run_id,),
        )
        run["events"] = cur.fetchall()
        return run


def list_runs(conn, user_id: UUID, limit: int = 25, offset: int = 0):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT id, kind, status, prompt, credential_mode, model_id, attempt_count,
                      error_code, tool_version_id, created_at, updated_at
               FROM runs WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            (user_id, limit, offset),
        )
        return cur.fetchall()
