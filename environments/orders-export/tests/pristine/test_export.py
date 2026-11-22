import csv
import io

import pytest

from app import app


@pytest.fixture()
def export_rows():
    resp = app.test_client().get("/export/orders.csv")
    assert resp.status_code == 200 and resp.mimetype == "text/csv"
    return list(csv.reader(io.StringIO(resp.get_data(as_text=True))))


def test_orders_export_columns(export_rows):
    assert export_rows[0] == ["order_id", "date", "total", "customer_name"]


def test_orders_export_one_row_per_order(export_rows):
    # 45 orders in the seed data, every status included
    assert len(export_rows) - 1 == 45
