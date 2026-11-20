import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StringConstraints, model_validator

from .. import deps
from .studio import Spec, Text, build_stream

router = APIRouter(prefix="/zeta", tags=["zeta"], dependencies=[Depends(deps.check_origin)])
FieldKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,31}$")]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class AppField(Spec):
    key: FieldKey
    label: Text
    type: Literal["text", "number", "currency", "date", "select", "checkbox"]
    options: list[Text] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def check_options(self):
        if self.key in {"constructor", "prototype"}:
            raise ValueError("Use a different field key")
        if self.type == "select":
            if len(self.options) < 2 or len(set(self.options)) != len(self.options):
                raise ValueError("Select fields need at least two distinct choices")
        elif self.options:
            raise ValueError("Only select fields can have options")
        return self


class CustomApp(Spec):
    name: Text
    description: Description
    entity: Text
    fields: list[AppField] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def check_field_keys(self):
        if len({field.key for field in self.fields}) != len(self.fields):
            raise ValueError("Field keys must be unique")
        return self


class CustomRequest(Spec):
    prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1600)]
    current: CustomApp | None = None


class SavedProject(Spec):
    app: CustomApp | None = None
    rows: list[dict] = Field(default_factory=list, max_length=1000)

    @model_validator(mode='after')
    def validate_rows(self):
        if len(json.dumps(self.rows)) > 500000:
            raise ValueError('Project records exceed the demo storage limit')
        keys = {field.key for field in self.app.fields} if self.app else set()
        ids = set()
        for row in self.rows:
            if set(row) != {'id', 'values'} or not isinstance(row['id'], str) or row['id'] in ids:
                raise ValueError('Records need unique string IDs and values')
            ids.add(row['id'])
            if not isinstance(row['values'], dict) or not set(row['values']).issubset(keys):
                raise ValueError('Record fields must belong to the current app')
            for value in row['values'].values():
                if not isinstance(value, (str, bool, int, float)) or len(str(value)) > 300:
                    raise ValueError('Invalid record value')
        return self


@router.get('/project')
def get_project(user=Depends(deps.current_user), conn=Depends(deps.get_conn)):
    deps.require_password_changed(user)
    with conn.cursor() as cur:
        cur.execute('SELECT project FROM custom_projects WHERE user_id = %s', (user.id,))
        row = cur.fetchone()
    return row[0] if row else {'app': None, 'rows': []}


@router.put('/project')
def save_project(payload: SavedProject, user=Depends(deps.current_user), conn=Depends(deps.get_conn)):
    from psycopg.types.json import Jsonb
    deps.require_password_changed(user)
    with conn.cursor() as cur:
        cur.execute('''INSERT INTO custom_projects(user_id, project) VALUES (%s, %s)
            ON CONFLICT(user_id) DO UPDATE SET
              previous_app = CASE WHEN custom_projects.project->'app' IS DISTINCT FROM EXCLUDED.project->'app'
                THEN custom_projects.project->'app' ELSE custom_projects.previous_app END,
              project = EXCLUDED.project, updated_at = now()''', (user.id, Jsonb(payload.model_dump())))
    return {'status': 'saved'}


def verify_revision(previous: CustomApp | None, proposed: CustomApp) -> None:
    if previous is None:
        return
    proposed_fields = {field.key: field for field in proposed.fields}
    for field in previous.fields:
        updated = proposed_fields.get(field.key)
        if updated is None or updated.type != field.type:
            raise ValueError(f"Keep the existing key and type for {field.key} to preserve saved records.")
        if not set(field.options).issubset(updated.options):
            raise ValueError(f"Keep existing choices for {field.key} to preserve saved records.")


@router.post("/build")
async def build(payload: CustomRequest, user: deps.CurrentUser = Depends(deps.current_user)):
    deps.require_password_changed(user)
    messages = [
        {"role": "system", "content": (
            "You design a small working record tracker. Return exactly one JSON object matching: "
            + json.dumps(CustomApp.model_json_schema())
            + ". Infer a concise app name, a one-sentence description, a singular record name and the fields "
            "for the user's workflow. The interface automatically gives them a form, a table, and add/edit/delete. "
            "Use stable snake_case field keys. For a select field provide at least two unique choices. "
            "For revisions, keep all existing field keys, types and choices and implement additive changes. "
            "Keep the description factual. Do not claim integrations, automation, permissions, or unsupported behavior. "
            "Do not output executable code, HTML, external links, or any sample personal data."
        )},
        {"role": "user", "content": json.dumps({
            "request": payload.prompt,
            "current": payload.current.model_dump() if payload.current else None,
        })},
    ]
    return build_stream(
        messages, CustomApp, payload.current,
        lambda proposal: verify_revision(payload.current, proposal),
        result_key="app",
        inspect="Read the request and the current app schema." if payload.current else "Read the request and started a new app.",
        check="Checking field keys, control types, options, and compatibility with saved records.",
    )

