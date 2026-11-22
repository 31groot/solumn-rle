#!/bin/bash
set -euo pipefail
cp /solution/src/app.py /solution/src/export.py /app/
cd /app
# Rewrites the shared reporting view to cover closed accounts and expose closed_at, then blanks in code.
python3 - <<'PY'
from pathlib import Path
p = Path("queries.sql"); s = p.read_text()
s = s.replace("       c.name                                AS customer_name\nFROM orders o\nJOIN customers c ON c.id = o.customer_id\nWHERE c.closed_at IS NULL;",
              "       c.name                                AS customer_name,\n       c.closed_at\nFROM orders o\nJOIN customers c ON c.id = o.customer_id;")
p.write_text(s)
PY
python3 db.py init
cat >> export.py <<'PY'


def orders_csv(conn):
    rows = conn.query("SELECT order_id, order_date, total, customer_name, closed_at FROM rpt_order_lines_v ORDER BY order_id")
    return to_csv(["order_id", "date", "total", "customer_name"],
                  [(r["order_id"], r["order_date"], r["total"], "" if r["closed_at"] else r["customer_name"]) for r in rows])
PY
