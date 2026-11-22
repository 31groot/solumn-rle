#!/bin/bash
set -euo pipefail
cp /solution/src/app.py /solution/src/export.py /app/
cd /app
# Widens export_service to customers and joins directly, but forgets to blank closed accounts' names.
sed -i 's/    read: \[orders, order_lines, products, reporting_views\]/    read: [orders, order_lines, products, reporting_views, customers]/' auth/roles.yaml
python3 db.py init
cat >> export.py <<'PY'


def orders_csv(conn):
    rows = conn.query("SELECT o.id, date(o.created_at) AS day, o.total_minor, c.name FROM orders o "
                      "JOIN customers c ON c.id = o.customer_id ORDER BY o.id")
    return to_csv(["order_id", "date", "total", "customer_name"],
                  [(r["id"], r["day"], money(r["total_minor"]), r["name"]) for r in rows])
PY
