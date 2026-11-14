"""Create the single demo workspace and synthetic CRM data.

Usage: python scripts/seed.py
Requires DATABASE_URL and migrations to have run. Idempotent: skips if the
demo workspace already has leads.
"""

import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "api" / ".env")
sys.path.insert(0, str(ROOT))

from api.config import SEED_WORKSPACE_SLUG  # noqa: E402

FIRST = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Ivy", "Owen", "Nora", "Caleb",
         "Mila", "Jonah", "Elena", "Marcus", "Priya", "Diego", "Hana", "Felix", "Rosa", "Kofi"]
LAST = ["Shah", "Okafor", "Novak", "Tanaka", "Silva", "Kaur", "Berg", "Costa", "Weber", "Dube"]
COMPANIES = [
    ("Northwind Traders", "Logistics", "https://northwind.example.com"),
    ("Bluepeak Software", "SaaS", "https://bluepeak.example.com"),
    ("Cedar & Pine Retail", "Retail", "https://cedarpine.example.com"),
    ("Helio Energy", "CleanTech", "https://helioenergy.example.com"),
    ("Maple Street Legal", "Legal", "https://maplestreet.example.com"),
    ("Quartz Health", "HealthTech", "https://quartzhealth.example.com"),
    ("Ironclad Security", "Cybersecurity", "https://ironcladsec.example.com"),
    ("Lumen Media", "Media", "https://lumenmedia.example.com"),
]
STAGES = ["new", "contacted", "qualified", "customer", "lost"]


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    rng = random.Random(42)
    today = date.today()

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO workspaces (name, slug) VALUES ('Demo workspace', %s) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            (SEED_WORKSPACE_SLUG,),
        )
        ws_id = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM entity_nodes WHERE workspace_id = %s AND type = 'lead'",
            (ws_id,),
        )
        if cur.fetchone()[0] > 0:
            print("demo workspace already seeded; nothing to do")
            return 0

        company_ids = []
        for name, industry, website in COMPANIES:
            cur.execute(
                "INSERT INTO entity_nodes (workspace_id, type, name) VALUES (%s,'company',%s) RETURNING id",
                (ws_id, name),
            )
            cid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO entity_traits (node_id, workspace_id, domain, schema_version, data) "
                "VALUES (%s,%s,'company',1,%s)",
                (cid, ws_id, Jsonb({"website": website, "industry": industry})),
            )
            company_ids.append(cid)

        lead_ids = []
        for i in range(30):
            first, last = rng.choice(FIRST), rng.choice(LAST)
            name = f"{first} {last}"
            company_id = rng.choice(company_ids)
            stage = rng.choice(STAGES)
            last_contact = today - timedelta(days=rng.randint(0, 45))
            value = round(Decimal(rng.randint(500, 50000)) / 100 * 100, 2)
            cur.execute(
                "INSERT INTO entity_nodes (workspace_id, type, name) VALUES (%s,'lead',%s) RETURNING id",
                (ws_id, name),
            )
            lid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO entity_traits (node_id, workspace_id, domain, schema_version, data) "
                "VALUES (%s,%s,'lead',1,%s)",
                (lid, ws_id, Jsonb({
                    "email": f"{first.lower()}.{last.lower()}{i}@example.com",
                    "company_id": str(company_id),
                    "stage": stage,
                    "last_contact_date": last_contact.isoformat(),
                    "value": str(value),
                    "currency": "USD",
                })),
            )
            cur.execute(
                "INSERT INTO entity_edges (workspace_id, src_node_id, dst_node_id, kind) "
                "VALUES (%s,%s,%s,'belongs_to')",
                (ws_id, lid, company_id),
            )
            lead_ids.append(lid)

        # A handful of activities and follow-up tasks.
        kinds = ["note", "call", "email", "meeting"]
        bodies = [
            "Intro call went well; send pricing deck.",
            "Asked for a demo next week.",
            "Renewal discussion scheduled.",
            "Requested security questionnaire.",
            "Follow up on pilot results.",
        ]
        for i in range(20):
            lid = rng.choice(lead_ids)
            kind = rng.choice(kinds)
            body = rng.choice(bodies)
            occurred = today - timedelta(days=rng.randint(0, 30))
            cur.execute(
                "INSERT INTO entity_nodes (workspace_id, type, name) VALUES (%s,'activity',%s) RETURNING id",
                (ws_id, f"{kind}: {body[:60]}"),
            )
            aid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO entity_traits (node_id, workspace_id, domain, schema_version, data) "
                "VALUES (%s,%s,'activity',1,%s)",
                (aid, ws_id, Jsonb({
                    "kind": kind, "body": body,
                    "occurred_at": f"{occurred.isoformat()}T12:00:00+00:00",
                })),
            )
            cur.execute(
                "INSERT INTO entity_edges (workspace_id, src_node_id, dst_node_id, kind) "
                "VALUES (%s,%s,%s,'about')",
                (ws_id, aid, lid),
            )

        titles = [
            "Send follow-up email", "Schedule demo call", "Share proposal",
            "Check in on pilot", "Prepare quarterly review",
        ]
        for i in range(15):
            lid = rng.choice(lead_ids)
            title = rng.choice(titles)
            due = today + timedelta(days=rng.randint(-5, 14))
            status = "done" if rng.random() < 0.3 else "open"
            cur.execute(
                "INSERT INTO entity_nodes (workspace_id, type, name) VALUES (%s,'task',%s) RETURNING id",
                (ws_id, title),
            )
            tid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO entity_traits (node_id, workspace_id, domain, schema_version, data) "
                "VALUES (%s,%s,'task',1,%s)",
                (tid, ws_id, Jsonb({
                    "title": title, "due_date": due.isoformat(),
                    "status": status, "lead_id": str(lid),
                })),
            )
            cur.execute(
                "INSERT INTO entity_edges (workspace_id, src_node_id, dst_node_id, kind) "
                "VALUES (%s,%s,%s,'about')",
                (ws_id, tid, lid),
            )

    print(f"seeded demo workspace '{SEED_WORKSPACE_SLUG}' with 8 companies, 30 leads, 20 activities, 15 tasks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
