# Contracts

Versioned JSON schemas for data crossing the API boundary. The FastAPI
Pydantic models in `api/schemas.py` are the authoritative runtime
validation; these files document the wire format for the frontend and
for generated tool bundles in Phase 2.

- `schemas/lead.schema.json` — CRM lead
- `schemas/company.schema.json` — CRM company
- `schemas/activity.schema.json` — note/call/email/meeting on a lead
- `schemas/task.schema.json` — follow-up task, optionally linked to a lead
- `schemas/error.schema.json` — `{detail, code?}` error body
- `examples/` — valid example payloads

Rules that apply to every record: IDs are UUIDs, workspace is implied by
the session (never sent by the client), `version` is an integer used for
optimistic locking — a stale update returns HTTP 409. Dates are ISO
`YYYY-MM-DD`; timestamps are ISO 8601 UTC. Money-like fields are decimal
strings with an explicit 3-letter currency; they are not a ledger.
