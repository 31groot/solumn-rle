"""Backfill jobs: compute derived columns for existing rows after a schema migration.

Usage: python3 backfill.py <job>     (in production, via scripts/run_job.sh)
"""
import argparse
import os
import sys
from datetime import datetime, timezone

import batcher
import db
from migrate import migrate


CALLING_CODE = {"IN": "91", "US": "1", "GB": "44"}


def normalize_email(email):
    email = email.strip().lower()
    local, _, domain = email.rpartition("@")
    if domain in ("gmail.com", "googlemail.com"):
        local, domain = local.split("+", 1)[0].replace(".", ""), "gmail.com"
    return f"{local}@{domain}"


def split_name(full_name):
    words = full_name.split()
    if not words:
        return "", ""
    if len(words) == 1:
        return words[0], ""
    return " ".join(words[:-1]), words[-1]


def to_e164(phone, country):
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    cc = CALLING_CODE[country]
    if digits.startswith(cc) and len(digits) == len(cc) + 10:
        national = digits[len(cc):]
    elif digits.startswith("0") and len(digits) == 11:
        national = digits[1:]
    else:
        national = digits
    return f"+{cc}{national}" if len(national) == 10 else None


def transform_user(row):
    first, last = split_name(row["full_name"])
    return {"email_normalized": normalize_email(row["email"]), "first_name": first, "last_name": last,
            "phone_e164": to_e164(row["phone"], row["country"])}


JOBS = {
    "users": {
        "table": "users",
        "columns": ("email", "full_name", "phone", "country"),
        "transform": transform_user,
    },
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_job(name, conn=None, batch_size=500, resume=False):
    spec = JOBS[name]
    conn = conn or db.connect()
    migrate(conn)
    after, initial, resumed_from = None, 0, None
    if resume:
        prev = conn.execute("SELECT run_id, status, cursor, rows_done FROM backfill_runs WHERE job = ? "
                            "ORDER BY started_at DESC, rowid DESC LIMIT 1", (name,)).fetchone()
        if prev is not None and prev["status"] == "complete":
            print(f"{name}: latest run {prev['run_id']} is complete, nothing to resume")
            return prev["rows_done"]
        if prev is not None:
            after, initial, resumed_from = prev["cursor"], prev["rows_done"], prev["run_id"]
            print(f"{name}: resuming run {resumed_from} after {initial} rows", file=sys.stderr)
    run_id = os.environ.get("JOB_RUN_ID") or f"manual-{os.getpid()}-{_now()}"
    with conn:
        conn.execute("INSERT INTO backfill_runs (run_id, job, started_at, rows_done, cursor, resumed_from, status) "
                     "VALUES (?, ?, ?, ?, ?, ?, 'running')", (run_id, name, _now(), initial, after, resumed_from))

    def progress(done, cursor):
        conn.execute("UPDATE backfill_runs SET rows_done = ?, cursor = ? WHERE run_id = ?", (done, cursor, run_id))

    try:
        done = batcher.run(conn, spec["table"], spec["columns"], spec["transform"], size=batch_size,
                           after=after, initial=initial, on_progress=progress)
    except BaseException:
        with conn:
            conn.execute("UPDATE backfill_runs SET status = 'failed', finished_at = ? WHERE run_id = ?",
                         (_now(), run_id))
        raise
    with conn:
        conn.execute("UPDATE backfill_runs SET status = 'complete', finished_at = ?, rows_done = ? "
                     "WHERE run_id = ?", (_now(), done, run_id))
    print(f"{name}: backfill complete, {done} rows (run {run_id})")
    return done


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a backfill job.")
    parser.add_argument("job", choices=sorted(JOBS))
    parser.add_argument("--resume", action="store_true",
                        help="continue the job's latest unfinished run from its last committed batch")
    args = parser.parse_args()
    run_job(args.job, resume=args.resume)
