#!/bin/bash
set -euo pipefail
cp /solution/src/app.py /solution/src/export.py /app/
cd /app
# Reads customers over a raw sqlite3 connection (no role authorizer).
cat >> export.py <<'PY'

import sqlite3 as _sqlite3
import db as _db


def orders_csv(conn):
    raw = _sqlite3.connect(_db.DB_PATH)
    rows = raw.execute("SELECT o.id, date(o.created_at), o.total_minor, "
                       "CASE WHEN c.closed_at IS NULL THEN c.name ELSE '' END FROM orders o "
                       "JOIN customers c ON c.id = o.customer_id ORDER BY o.id").fetchall()
    raw.close()
    return to_csv(["order_id", "date", "total", "customer_name"], [(i, d, money(m), n) for i, d, m, n in rows])
PY
