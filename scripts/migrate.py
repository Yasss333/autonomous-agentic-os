"""Apply SQL migrations in order. Uses DATABASE_DIRECT_URL when set
(Neon direct endpoint), falling back to DATABASE_URL.

Usage: python scripts/migrate.py
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "api" / ".env")

MIGRATIONS = ROOT / "migrations"


def main() -> int:
    url = os.environ.get("DATABASE_DIRECT_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        return 1

    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                       name text PRIMARY KEY,
                       applied_at timestamptz NOT NULL DEFAULT now()
                   )"""
            )
            cur.execute("SELECT name FROM schema_migrations")
            applied = {r[0] for r in cur.fetchall()}

        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in applied:
                print(f"skip  {path.name}")
                continue
            print(f"apply {path.name}")
            sql = path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,)
                )
    print("migrations complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
