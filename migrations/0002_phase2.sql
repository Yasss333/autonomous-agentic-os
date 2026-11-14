-- Phase 2: run kinds (generation vs tool invocation), idempotent run
-- creation, tool activation registry, and provider-key references.
-- The reviewer API key itself is never stored; only an opaque reference
-- that resolves to key material held in API process memory.

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'generate',
    ADD COLUMN IF NOT EXISTS input jsonb,
    ADD COLUMN IF NOT EXISTS tool_version_id uuid REFERENCES tool_versions(id),
    ADD COLUMN IF NOT EXISTS idempotency_key text,
    ADD COLUMN IF NOT EXISTS bundle jsonb;

ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_kind_check;
ALTER TABLE runs ADD CONSTRAINT runs_kind_check CHECK (kind IN ('generate', 'tool_invoke'));
ALTER TABLE runs ALTER COLUMN prompt DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS runs_idem_idx
    ON runs(user_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS tool_registry (
    workspace_id      uuid NOT NULL REFERENCES workspaces(id),
    name              text NOT NULL,
    active_version_id uuid REFERENCES tool_versions(id),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, name)
);

CREATE TABLE IF NOT EXISTS provider_key_refs (
    ref        text PRIMARY KEY,
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS provider_key_refs_user_idx ON provider_key_refs(user_id);

CREATE TABLE IF NOT EXISTS workers (
    worker_id  text PRIMARY KEY,
    last_seen  timestamptz NOT NULL DEFAULT now()
);

-- Invocation idempotency: one business effect per (workspace, key).
CREATE TABLE IF NOT EXISTS invocation_keys (
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    idem_key     text NOT NULL,
    run_id       uuid NOT NULL REFERENCES runs(id),
    created_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, idem_key)
);
