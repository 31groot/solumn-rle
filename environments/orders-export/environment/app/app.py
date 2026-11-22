"""Shop backend API."""
from flask import Flask, Response, abort, jsonify, request

import db
import export

app = Flask(__name__)


@app.errorhandler(db.PermissionDenied)
def permission_denied(err):
    return jsonify(error="permission denied", detail=str(err)), 403


def order_json(conn, row):
    lines = conn.query("SELECT sku, qty, price_minor FROM order_lines WHERE order_id = ? ORDER BY sku", (row["id"],))
    return {"id": row["id"], "customer_id": row["customer_id"], "created_at": row["created_at"],
            "status": row["status"], "total": export.money(row["total_minor"]),
            "lines": [dict(line) for line in lines]}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/orders")
def list_orders():
    status = request.args.get("status")
    with db.connect("orders_api") as conn:
        sql = "SELECT * FROM orders" + (" WHERE status = ?" if status else "") + " ORDER BY id"
        rows = conn.query(sql, (status,) if status else ())
        return jsonify([order_json(conn, r) for r in rows])


@app.get("/orders/<int:order_id>")
def get_order(order_id):
    with db.connect("orders_api") as conn:
        rows = conn.query("SELECT * FROM orders WHERE id = ?", (order_id,))
        if not rows:
            abort(404)
        return jsonify(order_json(conn, rows[0]))


@app.get("/customers/<int:customer_id>")
def get_customer(customer_id):
    with db.connect("support") as conn:
        rows = conn.query("SELECT id, name, email, phone FROM customers WHERE id = ?", (customer_id,))
        if not rows:
            abort(404)
        return jsonify(dict(rows[0]))


@app.get("/export/daily_sales.csv")
def daily_sales():
    with db.connect(export.EXPORT_ROLE) as conn:
        return Response(export.daily_sales_csv(conn), mimetype="text/csv")


if __name__ == "__main__":
    app.run(port=8000)
