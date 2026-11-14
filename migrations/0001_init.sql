-- Phase 1 schema: identity, sessions, generic CRM node/trait/edge model,
-- and the tables reserved for Phase 2 (runs, tools, usage, allowances).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS workspaces (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    slug        text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id         uuid NOT NULL REFERENCES workspaces(id),
    email                text NOT NULL UNIQUE,
    password_hash        text NOT NULL,
    must_change_password boolean NOT NULL DEFAULT true,
    status               text NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active', 'disabled')),
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    ip         text,
    user_agent text
);
CREATE INDEX IF NOT EXISTS sessions_user_idx ON sessions(user_id);
CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions(expires_at) WHERE revoked_at IS NULL;

-- Generic CRM model: nodes carry type/name/version; traits carry validated
-- domain JSON; edges carry relationships inside one workspace.

CREATE TABLE IF NOT EXISTS entity_nodes (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    type         text NOT NULL CHECK (type IN ('lead', 'company', 'activity', 'task')),
    name         text NOT NULL,
    version      integer NOT NULL DEFAULT 1,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS entity_nodes_ws_type_idx ON entity_nodes(workspace_id, type);

CREATE TABLE IF NOT EXISTS entity_traits (
    node_id            uuid NOT NULL REFERENCES entity_nodes(id) ON DELETE CASCADE,
    workspace_id       uuid NOT NULL REFERENCES workspaces(id),
    domain             text NOT NULL,
    schema_version     integer NOT NULL DEFAULT 1,
    data               jsonb NOT NULL,
    embedding          vector(384),
    embedding_model    text,
    embedding_content_version integer,
    updated_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (node_id, domain),
    UNIQUE (workspace_id, node_id, domain)
);
CREATE INDEX IF NOT EXISTS entity_traits_ws_domain_idx ON entity_traits(workspace_id, domain);

CREATE TABLE IF NOT EXISTS entity_edges (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    src_node_id  uuid NOT NULL REFERENCES entity_nodes(id) ON DELETE CASCADE,
    dst_node_id  uuid NOT NULL REFERENCES entity_nodes(id) ON DELETE CASCADE,
    kind         text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, src_node_id, dst_node_id, kind),
    CHECK (src_node_id <> dst_node_id)
);
CREATE INDEX IF NOT EXISTS entity_edges_src_idx ON entity_edges(workspace_id, src_node_id, kind);
CREATE INDEX IF NOT EXISTS entity_edges_dst_idx ON entity_edges(workspace_id, dst_node_id, kind);

-- Phase 2 reservations (created now so migrations stay additive later).

CREATE TABLE IF NOT EXISTS runs (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id  uuid NOT NULL REFERENCES workspaces(id),
    user_id       uuid NOT NULL REFERENCES users(id),
    status        text NOT NULL DEFAULT 'queued',
    prompt        text NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    credential_mode text NOT NULL DEFAULT 'sponsored',
    model_id      text,
    artifact_hash text,
    error_code    text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS runs_user_idx ON runs(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS run_events (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id     uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    seq        integer NOT NULL,
    kind       text NOT NULL,
    payload    jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, seq)
);

CREATE TABLE IF NOT EXISTS job_leases (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    worker_id    text NOT NULL,
    lease_token  text NOT NULL,
    generation   integer NOT NULL DEFAULT 1,
    expires_at   timestamptz NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    released_at  timestamptz
);
CREATE INDEX IF NOT EXISTS job_leases_run_idx ON job_leases(run_id) WHERE released_at IS NULL;

CREATE TABLE IF NOT EXISTS tool_versions (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id   uuid NOT NULL REFERENCES workspaces(id),
    name           text NOT NULL,
    version        integer NOT NULL,
    schema_version integer NOT NULL,
    source_hash    text NOT NULL,
    source_code    text NOT NULL,
    ui_spec        jsonb NOT NULL DEFAULT '{}',
    input_schema   jsonb NOT NULL DEFAULT '{}',
    output_schema  jsonb NOT NULL DEFAULT '{}',
    qa_result      jsonb,
    status         text NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft', 'passed', 'failed', 'active', 'retired')),
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, name, version)
);

CREATE TABLE IF NOT EXISTS usage_events (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workspace_id  uuid NOT NULL REFERENCES workspaces(id),
    user_id       uuid NOT NULL REFERENCES users(id),
    run_id        uuid REFERENCES runs(id) ON DELETE SET NULL,
    model_id      text NOT NULL,
    payer         text NOT NULL CHECK (payer IN ('sponsored', 'reviewer_key')),
    input_tokens  integer,
    output_tokens integer,
    cost_usd      numeric(12, 6),
    cost_known    boolean NOT NULL DEFAULT false,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS usage_events_day_idx ON usage_events(user_id, created_at);

CREATE TABLE IF NOT EXISTS demo_allowances (
    user_id          uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    sponsored_used_at timestamptz,
    reset_count      integer NOT NULL DEFAULT 0,
    updated_at       timestamptz NOT NULL DEFAULT now()
);
