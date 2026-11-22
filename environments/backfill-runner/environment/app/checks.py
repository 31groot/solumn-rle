"""Post-backfill data checks. Exit 0 when every check passes, 1 otherwise."""
import re
import sys

import db

CALLING_CODE = {"IN": "91", "US": "1", "GB": "44"}


def run_checks(conn):
    failures = []

    def fail(msg):
        failures.append(msg)

    versions = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
    if "0003_users_contact_columns" not in versions:
        return ["migration 0003_users_contact_columns not applied"]

    meta = dict(conn.execute("SELECT key, value FROM seed_meta").fetchall())
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if str(count) != meta.get("users_count"):
        fail(f"users row count {count} != {meta.get('users_count')}")
    if db.legacy_checksum(conn) != meta.get("users_legacy_sha256"):
        fail("legacy users columns were modified")

    last = conn.execute("SELECT status, rows_done FROM backfill_runs WHERE job = 'users' "
                        "ORDER BY started_at DESC, rowid DESC LIMIT 1").fetchone()
    if last is None or last["status"] != "complete" or last["rows_done"] != count:
        fail(f"latest users backfill run is not complete: {tuple(last) if last else None}")

    bad = {"email": 0, "name": 0, "phone": 0}
    examples = []
    for r in conn.execute("SELECT id, email, full_name, country, email_normalized, first_name, last_name, "
                          "phone_e164 FROM users"):
        en = r["email_normalized"]
        if en is None or en != en.strip().lower() or en.count("@") != 1 or (
                en.endswith("@gmail.com") and ("+" in en or "." in en.split("@")[0])):
            bad["email"] += 1
            examples.append((r["id"], "email", en))
        if r["first_name"] is None or r["last_name"] is None or \
                " ".join(filter(None, (r["first_name"], r["last_name"]))) != " ".join(r["full_name"].split()):
            bad["name"] += 1
            examples.append((r["id"], "name", r["first_name"], r["last_name"]))
        p = r["phone_e164"]
        if p is not None and not re.fullmatch(r"\+" + CALLING_CODE[r["country"]] + r"\d{10}", p):
            bad["phone"] += 1
            examples.append((r["id"], "phone", p))
    for k, v in bad.items():
        if v:
            fail(f"{v} rows with invalid {k} columns")
    if examples:
        fail(f"examples: {examples[:5]}")
    return failures


if __name__ == "__main__":
    problems = run_checks(db.connect())
    for p in problems:
        print("FAIL", p)
    print("checks passed" if not problems else f"{len(problems)} check(s) failed")
    sys.exit(1 if problems else 0)
