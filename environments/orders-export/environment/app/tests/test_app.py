import csv
import io

import pytest

import db
from app import app


@pytest.fixture()
def client():
    return app.test_client()


def test_health(client):
    assert client.get("/health").get_json() == {"ok": True}


def test_get_order(client):
    body = client.get("/orders/1001").get_json()
    assert body["id"] == 1001
    assert body["lines"]
    assert sum(line["qty"] * line["price_minor"] for line in body["lines"]) == round(float(body["total"]) * 100)


def test_list_orders_by_status(client):
    rows = client.get("/orders?status=cancelled").get_json()
    assert rows and all(r["status"] == "cancelled" for r in rows)


def test_customer_lookup(client):
    assert client.get("/customers/4").get_json()["name"] == "Patel, Gupta & Co."
    assert client.get("/customers/999").status_code == 404


def test_daily_sales_csv(client):
    resp = client.get("/export/daily_sales.csv")
    assert resp.status_code == 200 and resp.mimetype == "text/csv"
    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True))))
    assert rows[0] == ["day", "sku", "units", "revenue"]
    assert len(rows) > 1


def test_roles_are_enforced():
    with db.connect("orders_api") as conn, pytest.raises(db.PermissionDenied):
        conn.query("SELECT email FROM customers")
