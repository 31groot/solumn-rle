"""SQLite access and the deterministic fixture used to build data/app.db."""
import hashlib
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get("APP_DB", Path(__file__).resolve().parent / "data" / "app.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    country TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS seed_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""
LEGACY_COLS = ("id", "created_at", "email", "full_name", "phone", "country", "status")


def connect(path=None):
    conn = sqlite3.connect(str(path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def legacy_checksum(conn):
    h = hashlib.sha256()
    for row in conn.execute(f"SELECT {', '.join(LEGACY_COLS)} FROM users ORDER BY id"):
        h.update(repr(tuple(row)).encode())
    return h.hexdigest()


FIRST = ["Asha", "Rohan", "maria", "JOHN", "Li", "Fatima", "Oliver", "Priya", "Chen", "Anne-Marie", "Kofi", "Zoë"]
LAST = ["Sharma", "O'Neil", "garcia", "Smith", "van der Berg", "Nguyen", "Iyer", "Okafor", "MÜLLER", "Rossi"]
DOMAINS = ["gmail.com", "GoogleMail.com", "example.org", "corp.example.com", "yahoo.co.in", "Gmail.com"]


def _phone(rng, country):
    n = "".join(rng.choice("0123456789") for _ in range(10))
    n = str(rng.randint(6, 9)) + n[1:]
    style = rng.randrange(6)
    prefix = {"IN": "91", "US": "1", "GB": "44"}[country]
    if style == 0:
        return None
    if style == 1:
        return f"+{prefix} {n[:5]} {n[5:]}"
    if style == 2:
        return f"0{n}" if country != "US" else f"({n[:3]}) {n[3:6]}-{n[6:]}"
    if style == 3:
        return f"{prefix}-{n}"
    if style == 4:
        return n[:7]  # truncated legacy import
    return n


def seed(path, n, seed_value=7):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    rng = random.Random(seed_value)
    conn = connect(path)
    conn.executescript(SCHEMA)
    start = datetime(2019, 1, 1)
    rows = []
    for i in range(1, n + 1):
        country = rng.choice(["IN", "IN", "US", "GB"])
        first, last = rng.choice(FIRST), rng.choice(LAST)
        local = rng.choice([f"{first}.{last}", f"{first}{i}", f"{first}+news", f"{last}.{first}+{i}"])
        local = local.replace(" ", "").replace("'", "")
        email = rng.choice(["", " ", ""]) + f"{local}@{rng.choice(DOMAINS)}" + rng.choice(["", "  "])
        name = rng.choice([f"{first} {last}", f"  {first}   {last} ", first, f"{first} M. {last}", ""])
        created = start + timedelta(minutes=rng.randrange(0, 60 * 24 * 365 * 5))
        rows.append((i, created.isoformat(timespec="seconds"), email, name, _phone(rng, country), country,
                     rng.choice(["active", "active", "disabled", "pending"])))
    conn.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    conn.execute("INSERT INTO seed_meta VALUES ('users_count', ?)", (str(n),))
    conn.execute("INSERT INTO seed_meta VALUES ('users_legacy_sha256', ?)", (legacy_checksum(conn),))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else DB_PATH, int(sys.argv[2]) if len(sys.argv) > 2 else 1_200_000)
