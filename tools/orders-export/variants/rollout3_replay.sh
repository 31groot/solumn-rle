#!/bin/bash
# Replays the file-editing commands of rollout3 (step 4 of agent/trajectory.json, verbatim) on the
# shipped repo, so the fixed grader can re-grade that rollout's end state.
set -euo pipefail
cd /app
python - <<'PY'
from pathlib import Path

path = Path('app.py')
text = path.read_text()
text = text.replace('\n\nif __name__ == "__main__":', '\n\n@app.get("/export/orders.csv")\ndef orders_csv():\n    with db.connect(export.EXPORT_ROLE) as conn:\n        return Response(export.orders_csv(conn), mimetype="text/csv")\n\n\nif __name__ == "__main__":')
path.write_text(text)

path = Path('export.py')
text = path.read_text()
text += '''\n\ndef orders_csv(conn):
    """All orders, with customer names only for accounts still open."""
    rows = conn.query(
        """
        SELECT o.id AS order_id, date(o.created_at) AS day, o.total_minor,
               r.customer_name
        FROM orders o
        LEFT JOIN rpt_order_lines_v r ON r.order_id = o.id
        ORDER BY o.id
        """
    )
    return to_csv(["order_id", "date", "total", "customer_name"],
                  [(r["order_id"], r["day"], money(r["total_minor"]), r["customer_name"]) for r in rows])
'''
path.write_text(text)
PY
python - <<'PY'
from pathlib import Path
path = Path('tests/test_export.py')
text = path.read_text().replace('import io\n', 'import io\nfrom datetime import datetime, timezone\nfrom decimal import Decimal\n').replace('from app import app\n', 'import db\nfrom app import app\n')
text += '''\n\ndef test_orders_export_values_and_closed_accounts(export_rows):
    with db.connect("support") as conn:
        orders = conn.query(
            """
            SELECT o.id, o.created_at, o.total_minor, c.name, c.closed_at
            FROM orders o JOIN customers c ON c.id = o.customer_id
            ORDER BY o.id
            """
        )
    expected = [
        [str(o["id"]),
         datetime.fromisoformat(o["created_at"]).astimezone(timezone.utc).strftime("%Y-%m-%d"),
         format(Decimal(o["total_minor"]) / 100, ".2f"),
         o["name"] if o["closed_at"] is None else ""]
        for o in orders
    ]
    assert any(o["closed_at"] is not None for o in orders)
    assert export_rows[1:] == expected


def test_orders_export_csv_escaping():
    body = app.test_client().get("/export/orders.csv").get_data(as_text=True)
    assert '"Patel, Gupta & Co."' in body
    assert '"Lakshmi ""Lucky"" Menon"' in body


def test_orders_export_uses_export_role(monkeypatch):
    roles = []
    connect = db.connect

    def recording_connect(role):
        roles.append(role)
        return connect(role)

    monkeypatch.setattr(db, "connect", recording_connect)
    assert app.test_client().get("/export/orders.csv").status_code == 200
    assert roles == ["export_service"]
'''
path.write_text(text)
PY
python -m pytest
python3 -m pytest -q
