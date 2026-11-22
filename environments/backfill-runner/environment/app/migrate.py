"""Schema migrations. Each migration runs once and is recorded in schema_migrations."""
from datetime import datetime, timezone

import db

MIGRATIONS = [
    ("0001_backfill_runs", """
        CREATE TABLE backfill_runs (
            run_id TEXT PRIMARY KEY,
            job TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            rows_done INTEGER NOT NULL DEFAULT 0,
            cursor TEXT,
            resumed_from TEXT,
            status TEXT NOT NULL
        );
    """),
    ("0002_users_status_index", "CREATE INDEX idx_users_status ON users(status);"),
    ("0003_users_contact_columns", """
        ALTER TABLE users ADD COLUMN email_normalized TEXT;
        ALTER TABLE users ADD COLUMN first_name TEXT;
        ALTER TABLE users ADD COLUMN last_name TEXT;
        ALTER TABLE users ADD COLUMN phone_e164 TEXT;
    """),
]


def applied(conn):
    return {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}


def migrate(conn):
    """Apply pending migrations in order; returns the versions applied by this call."""
    done, new = applied(conn), []
    for version, sql in MIGRATIONS:
        if version in done:
            continue
        with conn:
            for stmt in filter(str.strip, sql.split(";")):
                conn.execute(stmt)
            conn.execute("INSERT INTO schema_migrations VALUES (?, ?)",
                         (version, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        new.append(version)
    return new


if __name__ == "__main__":
    c = db.connect()
    print("applied:", migrate(c) or "nothing pending")
