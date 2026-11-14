"""Owner-only invite provisioning. Creates a user in the demo workspace with
a temporary password; the user must change it on first login.

Usage:
    python scripts/provision_user.py reviewer@example.com
    python scripts/provision_user.py reviewer@example.com --password 'Temp-Pass-123'

If --password is omitted, a random temporary password is printed once.
Never commit real credentials.
"""

import argparse
import os
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
    parser.add_argument("--password")
    parser.add_argument("--workspace", default=SEED_WORKSPACE_SLUG)
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    password = args.password or "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
    )

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM workspaces WHERE slug = %s", (args.workspace,))
        row = cur.fetchone()
        if not row:
            print(f"workspace '{args.workspace}' not found; run scripts/seed.py first", file=sys.stderr)
            return 1
        ws_id = row[0]
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
        user_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO demo_allowances (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (user_id,),
        )

    print(f"invited {args.email} in workspace '{args.workspace}' (user {user_id})")
    print(f"temporary password: {password}")
    print("Share it privately. The user must set a new password on first login.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
