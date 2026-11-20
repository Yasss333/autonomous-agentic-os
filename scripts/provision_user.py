"""Owner-only invite provisioning. Creates a user in the demo workspace with
a temporary password; the user must change it on first login.

Usage:
    python scripts/provision_user.py reviewer@example.com
    python scripts/provision_user.py reviewer@example.com --password 'Temp-Pass-123'
    python scripts/provision_user.py reviewer@example.com --clerk-user-id user_...

If --password is omitted, a random temporary password is printed once.
Never commit real credentials.
"""

import argparse
import os
import re
import secrets
import string
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "api" / ".env")
sys.path.insert(0, str(ROOT))

from api.config import SEED_WORKSPACE_SLUG  # noqa: E402
from api.security import hash_password  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    credentials = parser.add_mutually_exclusive_group()
    credentials.add_argument("--password")
    credentials.add_argument("--clerk-user-id", help="Clerk user ID from the dashboard")
    parser.add_argument("--workspace", default=SEED_WORKSPACE_SLUG)
    args = parser.parse_args()
    if args.clerk_user_id and not re.fullmatch(r"user_[A-Za-z0-9]+", args.clerk_user_id):
        parser.error("Expected a Clerk user ID starting with user_")

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    password = secrets.token_urlsafe(32) if args.clerk_user_id else args.password or "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
    )

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM workspaces WHERE slug = %s", (args.workspace,))
        row = cur.fetchone()
        if not row:
            print(f"workspace '{args.workspace}' not found; run scripts/seed.py first", file=sys.stderr)
            return 1
        ws_id = row[0]
        if args.clerk_user_id:
            try:
                cur.execute(
                    """INSERT INTO users (workspace_id, email, password_hash, clerk_user_id)
                       VALUES (%s, lower(%s), %s, %s)
                       ON CONFLICT (email) DO UPDATE SET clerk_user_id = EXCLUDED.clerk_user_id
                       WHERE users.workspace_id = EXCLUDED.workspace_id
                         AND users.status = 'active'
                         AND (users.clerk_user_id IS NULL OR users.clerk_user_id = EXCLUDED.clerk_user_id)
                       RETURNING id""",
                    (ws_id, args.email, hash_password(password), args.clerk_user_id),
                )
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                print("That Clerk user ID is already linked to another account.", file=sys.stderr)
                return 1
        else:
            cur.execute(
                """INSERT INTO users (workspace_id, email, password_hash, must_change_password)
                   VALUES (%s, lower(%s), %s, true)
                   ON CONFLICT (email) DO UPDATE
                     SET password_hash = EXCLUDED.password_hash,
                         must_change_password = true,
                         status = 'active'
                   RETURNING id""",
                (ws_id, args.email, hash_password(password)),
            )
        row = cur.fetchone()
        if not row:
            print("Existing account is disabled, linked to a different Clerk user, or in another workspace.", file=sys.stderr)
            return 1
        user_id = row[0]
        cur.execute(
            "INSERT INTO demo_allowances (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (user_id,),
        )

    if args.clerk_user_id:
        print(f"linked {args.email} in workspace '{args.workspace}' (user {user_id})")
        return 0
    print(f"invited {args.email} in workspace '{args.workspace}' (user {user_id})")
    print(f"temporary password: {password}")
    print("Share it privately. The user must set a new password on first login.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
