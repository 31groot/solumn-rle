Finance needs an order export from the shop backend.

Please add `GET /export/orders.csv` to `app.py`. It should return a CSV (`text/csv`) with a
header row and one row per order (every status), ordered by order id, with these columns in
this order:

    order_id,date,total,customer_name

- `date` is the order's `created_at` date (UTC) as `YYYY-MM-DD`
- `total` is the order total in rupees with two decimals, e.g. `129.99`
- `customer_name` is the name of the customer who placed the order; leave it empty for
  customers whose account is closed (we don't export names of closed accounts)
- values containing commas or quotes are quoted the standard CSV way

Like the other export endpoints, it runs under the existing `export_service` role.
`tests/test_export.py` already covers the new endpoint and currently fails; `python -m pytest`
should pass when you're done, and the existing endpoints must keep working. You can run the app
with `python app.py` or test it with Flask's test client.
