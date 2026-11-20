CREATE TABLE IF NOT EXISTS custom_projects (
    user_id uuid PRIMARY KEY REFERENCES users(id),
    project jsonb NOT NULL DEFAULT '{"app": null, "rows": []}',
    previous_app jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);
