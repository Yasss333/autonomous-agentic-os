"""Data access for the generic node/trait/edge CRM model.

Every function takes an open psycopg connection and runs inside the
request transaction. workspace_id always comes from the authenticated
user, never from client input.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .schemas import (
    ActivityCreate,
    ActivityOut,
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    LeadCreate,
    LeadDetail,
    LeadOut,
    LeadUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

DOMAIN_BY_TYPE = {
    "lead": "lead",
    "company": "company",
    "activity": "activity",
    "task": "task",
}

NODE_COLS = "n.id, n.type, n.name, n.version, n.created_at, n.updated_at"


def _node(row: dict) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "name": row["name"],
        "version": row["version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get_node(cur, workspace_id: UUID, node_id: UUID, node_type: str, for_update=False):
    cur.execute(
        f"SELECT {NODE_COLS} FROM entity_nodes n "
        f"WHERE n.id = %s AND n.workspace_id = %s AND n.type = %s"
        + (" FOR UPDATE" if for_update else ""),
        (node_id, workspace_id, node_type),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"{node_type.capitalize()} not found")
    return row


def _get_traits(cur, node_id: UUID) -> dict:
    cur.execute(
        "SELECT domain, data FROM entity_traits WHERE node_id = %s",
        (node_id,),
    )
    rows = cur.fetchall()
    out = {}
    for r in rows:
        out[r["domain"]] = r["data"]
    return out


def _insert_node(cur, workspace_id: UUID, node_type: str, name: str, data: dict, domain: str):
    cur.execute(
        "INSERT INTO entity_nodes (workspace_id, type, name) VALUES (%s, %s, %s) RETURNING id",
        (workspace_id, node_type, name),
    )
    node_id = cur.fetchone()["id"]
    cur.execute(
        """INSERT INTO entity_traits (node_id, workspace_id, domain, schema_version, data)
           VALUES (%s, %s, %s, 1, %s)""",
        (node_id, workspace_id, domain, Jsonb(data)),
    )
    return node_id


def _link(cur, workspace_id: UUID, src: UUID, dst: UUID, kind: str):
    cur.execute(
        """INSERT INTO entity_edges (workspace_id, src_node_id, dst_node_id, kind)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (workspace_id, src_node_id, dst_node_id, kind) DO NOTHING""",
        (workspace_id, src, dst, kind),
    )


def _unlink_kind(cur, workspace_id: UUID, src: UUID, kind: str):
    cur.execute(
        "DELETE FROM entity_edges WHERE workspace_id = %s AND src_node_id = %s AND kind = %s",
        (workspace_id, src, kind),
    )


def _assert_company(cur, workspace_id: UUID, company_id: UUID):
    cur.execute(
        "SELECT 1 FROM entity_nodes WHERE id = %s AND workspace_id = %s AND type = 'company'",
        (company_id, workspace_id),
    )
    if not cur.fetchone():
        raise HTTPException(400, "company_id does not reference a company in this workspace")


def _assert_lead(cur, workspace_id: UUID, lead_id: UUID):
    cur.execute(
        "SELECT 1 FROM entity_nodes WHERE id = %s AND workspace_id = %s AND type = 'lead'",
        (lead_id, workspace_id),
    )
    if not cur.fetchone():
        raise HTTPException(400, "lead_id does not reference a lead in this workspace")


def _bump_and_write(cur, node_id: UUID, workspace_id: UUID, data: dict, expected_version: int):
    cur.execute(
        """UPDATE entity_nodes
           SET version = version + 1, updated_at = now()
           WHERE id = %s AND workspace_id = %s AND version = %s""",
        (node_id, workspace_id, expected_version),
    )
    if cur.rowcount == 0:
        raise HTTPException(409, "Record was modified by someone else. Reload and retry.")
    cur.execute(
        "UPDATE entity_traits SET data = %s, updated_at = now() WHERE node_id = %s",
        (Jsonb(data), node_id),
    )


# ---------- Leads ----------


def _lead_out(row: dict, traits: dict, company_name: str | None = None) -> LeadOut:
    data = traits.get("lead", {})
    return LeadOut(
        **_node(row),
        email=data.get("email", ""),
        company_id=data.get("company_id"),
        company_name=company_name,
        stage=data.get("stage", "new"),
        last_contact_date=data.get("last_contact_date"),
        value=data.get("value"),
        currency=data.get("currency", "USD"),
    )


def create_lead(conn, workspace_id: UUID, payload: LeadCreate) -> LeadOut:
    with conn.cursor(row_factory=dict_row) as cur:
        if payload.company_id:
            _assert_company(cur, workspace_id, payload.company_id)
        data = {
            "email": str(payload.email),
            "company_id": str(payload.company_id) if payload.company_id else None,
            "stage": payload.stage,
            "last_contact_date": payload.last_contact_date.isoformat() if payload.last_contact_date else None,
            "value": str(payload.value) if payload.value is not None else None,
            "currency": payload.currency.upper(),
        }
        node_id = _insert_node(cur, workspace_id, "lead", payload.name, data, "lead")
        if payload.company_id:
            _link(cur, workspace_id, node_id, payload.company_id, "belongs_to")
        row = _get_node(cur, workspace_id, node_id, "lead")
        company_name = None
        if payload.company_id:
            cur.execute(
                "SELECT name FROM entity_nodes WHERE id = %s", (payload.company_id,)
            )
            company_name = cur.fetchone()["name"]
        return _lead_out(row, {"lead": data}, company_name)


def _lead_company_name(cur, workspace_id: UUID, lead_id: UUID) -> str | None:
    cur.execute(
        """SELECT c.name FROM entity_edges e
           JOIN entity_nodes c ON c.id = e.dst_node_id
           WHERE e.workspace_id = %s AND e.src_node_id = %s
             AND e.kind = 'belongs_to' AND c.type = 'company'""",
        (workspace_id, lead_id),
    )
    row = cur.fetchone()
    return row["name"] if row else None


def list_leads(conn, workspace_id: UUID, limit: int, offset: int, search: str | None, stage: str | None):
    with conn.cursor(row_factory=dict_row) as cur:
        where = ["n.workspace_id = %s", "n.type = 'lead'"]
        params: list = [workspace_id]
        if stage:
            where.append("t.data->>'stage' = %s")
            params.append(stage)
        if search:
            where.append(
                "(n.name ILIKE %s OR t.data->>'email' ILIKE %s OR c.name ILIKE %s)"
            )
            like = f"%{search}%"
            params += [like, like, like]
        where_sql = " AND ".join(where)
        cur.execute(
            f"""SELECT {NODE_COLS}, t.data AS traits, c.name AS company_name
                FROM entity_nodes n
                JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'lead'
                LEFT JOIN entity_edges e ON e.workspace_id = n.workspace_id
                     AND e.src_node_id = n.id AND e.kind = 'belongs_to'
                LEFT JOIN entity_nodes c ON c.id = e.dst_node_id AND c.type = 'company'
                WHERE {where_sql}
                ORDER BY n.updated_at DESC
                LIMIT %s OFFSET %s""",
            (*params, limit, offset),
        )
        rows = cur.fetchall()
        cur.execute(
            f"""SELECT count(*) AS total FROM entity_nodes n
                JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'lead'
                LEFT JOIN entity_edges e ON e.workspace_id = n.workspace_id
                     AND e.src_node_id = n.id AND e.kind = 'belongs_to'
                LEFT JOIN entity_nodes c ON c.id = e.dst_node_id AND c.type = 'company'
                WHERE {where_sql}""",
            params,
        )
        total = cur.fetchone()["total"]
        items = [
            _lead_out(r, {"lead": r["traits"]}, r["company_name"]) for r in rows
        ]
        return items, total


def get_lead(conn, workspace_id: UUID, lead_id: UUID) -> LeadDetail:
    with conn.cursor(row_factory=dict_row) as cur:
        row = _get_node(cur, workspace_id, lead_id, "lead")
        traits = _get_traits(cur, lead_id)
        company_name = _lead_company_name(cur, workspace_id, lead_id)
        lead = _lead_out(row, traits, company_name)

        cur.execute(
            """SELECT n.id, n.type, n.name, n.version, n.created_at, n.updated_at,
                      t.data AS traits
               FROM entity_edges e
               JOIN entity_nodes n ON n.id = e.src_node_id
               JOIN entity_traits t ON t.node_id = n.id
               WHERE e.workspace_id = %s AND e.dst_node_id = %s
                 AND e.kind = 'about' AND n.type IN ('activity', 'task')
               ORDER BY n.created_at DESC""",
            (workspace_id, lead_id),
        )
        activities: list[ActivityOut] = []
        tasks: list[TaskOut] = []
        for r in cur.fetchall():
            data = r["traits"]
            if r["type"] == "activity":
                activities.append(
                    ActivityOut(
                        **_node(r),
                        kind=data.get("kind", "note"),
                        body=data.get("body", ""),
                        occurred_at=data.get("occurred_at"),
                        lead_id=lead_id,
                    )
                )
            else:
                tasks.append(
                    TaskOut(
                        **_node(r),
                        title=data.get("title", ""),
                        due_date=data.get("due_date"),
                        status=data.get("status", "open"),
                        lead_id=lead_id,
                    )
                )
        return LeadDetail(**lead.model_dump(), activities=activities, tasks=tasks)


def update_lead(conn, workspace_id: UUID, lead_id: UUID, payload: LeadUpdate) -> LeadOut:
    with conn.cursor(row_factory=dict_row) as cur:
        _get_node(cur, workspace_id, lead_id, "lead", for_update=True)
        traits = _get_traits(cur, lead_id)
        data = dict(traits.get("lead", {}))
        changes = payload.model_dump(exclude_unset=True, exclude={"version"})
        if "email" in changes and changes["email"] is not None:
            changes["email"] = str(changes["email"])
        if "company_id" in changes:
            cid = changes["company_id"]
            if cid is not None:
                _assert_company(cur, workspace_id, cid)
                changes["company_id"] = str(cid)
        if "last_contact_date" in changes and changes["last_contact_date"] is not None:
            changes["last_contact_date"] = changes["last_contact_date"].isoformat()
        if "value" in changes and changes["value"] is not None:
            changes["value"] = str(changes["value"])
        if "currency" in changes and changes["currency"] is not None:
            changes["currency"] = changes["currency"].upper()
        if "name" in changes and changes["name"] is not None:
            cur.execute(
                "UPDATE entity_nodes SET name = %s WHERE id = %s",
                (changes["name"], lead_id),
            )
        data.update(
            {k: v for k, v in changes.items() if k != "name" and (v is not None or k in {
                "last_contact_date", "value", "company_id"
            })}
        )
        # Explicit nulls clear optional fields only when key was sent as null.
        for key in ("last_contact_date", "value", "company_id"):
            if key in changes and changes[key] is None:
                data[key] = None
        _bump_and_write(cur, lead_id, workspace_id, data, payload.version)
        _unlink_kind(cur, workspace_id, lead_id, "belongs_to")
        new_company = data.get("company_id")
        if new_company:
            _link(cur, workspace_id, lead_id, UUID(new_company), "belongs_to")
        row = _get_node(cur, workspace_id, lead_id, "lead")
        company_name = _lead_company_name(cur, workspace_id, lead_id)
        return _lead_out(row, {"lead": data}, company_name)


# ---------- Companies ----------


def _company_out(row: dict, traits: dict) -> CompanyOut:
    data = traits.get("company", {})
    return CompanyOut(
        **_node(row),
        website=data.get("website"),
        industry=data.get("industry"),
    )


def create_company(conn, workspace_id: UUID, payload: CompanyCreate) -> CompanyOut:
    with conn.cursor(row_factory=dict_row) as cur:
        data = {"website": payload.website, "industry": payload.industry}
        node_id = _insert_node(cur, workspace_id, "company", payload.name, data, "company")
        row = _get_node(cur, workspace_id, node_id, "company")
        return _company_out(row, {"company": data})


def list_companies(conn, workspace_id: UUID, limit: int, offset: int, search: str | None):
    with conn.cursor(row_factory=dict_row) as cur:
        where = ["n.workspace_id = %s", "n.type = 'company'"]
        params: list = [workspace_id]
        if search:
            where.append("(n.name ILIKE %s OR t.data->>'industry' ILIKE %s)")
            params += [f"%{search}%", f"%{search}%"]
        where_sql = " AND ".join(where)
        cur.execute(
            f"""SELECT {NODE_COLS}, t.data AS traits
                FROM entity_nodes n
                JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'company'
                WHERE {where_sql}
                ORDER BY n.name ASC
                LIMIT %s OFFSET %s""",
            (*params, limit, offset),
        )
        rows = cur.fetchall()
        cur.execute(
            f"""SELECT count(*) AS total FROM entity_nodes n
                JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'company'
                WHERE {where_sql}""",
            params,
        )
        total = cur.fetchone()["total"]
        items = [_company_out(r, {"company": r["traits"]}) for r in rows]
        return items, total


def update_company(conn, workspace_id: UUID, company_id: UUID, payload: CompanyUpdate) -> CompanyOut:
    with conn.cursor(row_factory=dict_row) as cur:
        _get_node(cur, workspace_id, company_id, "company", for_update=True)
        traits = _get_traits(cur, company_id)
        data = dict(traits.get("company", {}))
        changes = payload.model_dump(exclude_unset=True, exclude={"version"})
        for key in ("website", "industry"):
            if key in changes:
                data[key] = changes[key]
        if "name" in changes and changes["name"] is not None:
            cur.execute(
                "UPDATE entity_nodes SET name = %s WHERE id = %s",
                (changes["name"], company_id),
            )
        _bump_and_write(cur, company_id, workspace_id, data, payload.version)
        row = _get_node(cur, workspace_id, company_id, "company")
        return _company_out(row, {"company": data})


# ---------- Activities ----------


def add_activity(conn, workspace_id: UUID, lead_id: UUID, payload: ActivityCreate) -> ActivityOut:
    with conn.cursor(row_factory=dict_row) as cur:
        _assert_lead(cur, workspace_id, lead_id)
        data = {
            "kind": payload.kind,
            "body": payload.body,
            "occurred_at": (payload.occurred_at or datetime.now()).isoformat(),
        }
        name = f"{payload.kind}: {payload.body[:60]}"
        node_id = _insert_node(cur, workspace_id, "activity", name, data, "activity")
        _link(cur, workspace_id, node_id, lead_id, "about")
        row = _get_node(cur, workspace_id, node_id, "activity")
        return ActivityOut(
            **_node(row),
            kind=data["kind"],
            body=data["body"],
            occurred_at=data["occurred_at"],
            lead_id=lead_id,
        )


# ---------- Tasks ----------


def _task_out(row: dict, traits: dict, lead_id: UUID | None = None) -> TaskOut:
    data = traits.get("task", {})
    return TaskOut(
        **_node(row),
        title=data.get("title", ""),
        due_date=data.get("due_date"),
        status=data.get("status", "open"),
        lead_id=lead_id or data.get("lead_id"),
    )


def _task_lead_id(cur, workspace_id: UUID, task_id: UUID) -> UUID | None:
    cur.execute(
        """SELECT dst_node_id FROM entity_edges
           WHERE workspace_id = %s AND src_node_id = %s AND kind = 'about'""",
        (workspace_id, task_id),
    )
    row = cur.fetchone()
    return row["dst_node_id"] if row else None


def create_task(conn, workspace_id: UUID, payload: TaskCreate) -> TaskOut:
    with conn.cursor(row_factory=dict_row) as cur:
        if payload.lead_id:
            _assert_lead(cur, workspace_id, payload.lead_id)
        data = {
            "title": payload.title,
            "due_date": payload.due_date.isoformat(),
            "status": payload.status,
            "lead_id": str(payload.lead_id) if payload.lead_id else None,
        }
        node_id = _insert_node(cur, workspace_id, "task", payload.title, data, "task")
        if payload.lead_id:
            _link(cur, workspace_id, node_id, payload.lead_id, "about")
        row = _get_node(cur, workspace_id, node_id, "task")
        return _task_out(row, {"task": data}, payload.lead_id)


def list_tasks(conn, workspace_id: UUID, limit: int, offset: int, status: str | None, lead_id: UUID | None):
    with conn.cursor(row_factory=dict_row) as cur:
        where = ["n.workspace_id = %s", "n.type = 'task'"]
        params: list = [workspace_id]
        if status:
            where.append("t.data->>'status' = %s")
            params.append(status)
        join_edge = ""
        if lead_id:
            join_edge = "JOIN entity_edges el ON el.workspace_id = n.workspace_id AND el.src_node_id = n.id AND el.kind = 'about' AND el.dst_node_id = %s"
            params.append(lead_id)
            where.append("el.dst_node_id IS NOT NULL")
        where_sql = " AND ".join(where)
        cur.execute(
            f"""SELECT {NODE_COLS}, t.data AS traits
                FROM entity_nodes n
                JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'task'
                {join_edge}
                WHERE {where_sql}
                ORDER BY t.data->>'due_date' ASC NULLS LAST, n.created_at DESC
                LIMIT %s OFFSET %s""",
            (*params, limit, offset),
        )
        rows = cur.fetchall()
        cur.execute(
            f"""SELECT count(*) AS total FROM entity_nodes n
                JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'task'
                {join_edge}
                WHERE {where_sql}""",
            params,
        )
        total = cur.fetchone()["total"]
        items = []
        for r in rows:
            lid = None
            data = r["traits"]
            if data.get("lead_id"):
                lid = UUID(data["lead_id"])
            items.append(_task_out(r, {"task": data}, lid))
        return items, total


def update_task(conn, workspace_id: UUID, task_id: UUID, payload: TaskUpdate) -> TaskOut:
    with conn.cursor(row_factory=dict_row) as cur:
        _get_node(cur, workspace_id, task_id, "task", for_update=True)
        traits = _get_traits(cur, task_id)
        data = dict(traits.get("task", {}))
        changes = payload.model_dump(exclude_unset=True, exclude={"version"})
        for key in ("title", "status"):
            if key in changes and changes[key] is not None:
                data[key] = changes[key]
        if "due_date" in changes and changes["due_date"] is not None:
            data["due_date"] = changes["due_date"].isoformat()
        if "title" in changes and changes["title"] is not None:
            cur.execute(
                "UPDATE entity_nodes SET name = %s WHERE id = %s",
                (changes["title"], task_id),
            )
        _bump_and_write(cur, task_id, workspace_id, data, payload.version)
        row = _get_node(cur, workspace_id, task_id, "task")
        lid = _task_lead_id(cur, workspace_id, task_id)
        return _task_out(row, {"task": data}, lid)


# ---------- Search ----------


def search(conn, workspace_id: UUID, query: str, limit: int = 20):
    with conn.cursor(row_factory=dict_row) as cur:
        like = f"%{query}%"
        leads, _ = [], 0
        cur.execute(
            """SELECT n.id FROM entity_nodes n
               WHERE n.workspace_id = %s AND n.type = 'lead' AND n.name ILIKE %s
               LIMIT %s""",
            (workspace_id, like, limit),
        )
        lead_ids = [r["id"] for r in cur.fetchall()]
        if lead_ids:
            cur.execute(
                """SELECT n.id, n.type, n.name, n.version, n.created_at, n.updated_at,
                          t.data AS traits
                   FROM entity_nodes n
                   JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'lead'
                   WHERE n.id = ANY(%s)""",
                (lead_ids,),
            )
            for r in cur.fetchall():
                leads.append(_lead_out(r, {"lead": r["traits"]}))
        cur.execute(
            """SELECT n.id, n.type, n.name, n.version, n.created_at, n.updated_at,
                      t.data AS traits
               FROM entity_nodes n
               JOIN entity_traits t ON t.node_id = n.id AND t.domain = 'company'
               WHERE n.workspace_id = %s AND n.type = 'company'
                 AND (n.name ILIKE %s OR t.data->>'industry' ILIKE %s)
               LIMIT %s""",
            (workspace_id, like, like, limit),
        )
        companies = [_company_out(r, {"company": r["traits"]}) for r in cur.fetchall()]
        return {"leads": leads, "companies": companies}
