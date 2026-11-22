"""CSV exports served to the finance and ops tooling (role: export_service)."""
import csv
import io

EXPORT_ROLE = "export_service"


def money(minor):
    """12999 -> '129.99'"""
    sign = "-" if minor < 0 else ""
    minor = abs(minor)
    return f"{sign}{minor // 100}.{minor % 100:02d}"


def to_csv(columns, rows):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buf.getvalue()


def daily_sales_csv(conn):
    """Units and revenue per product per day, paid and shipped orders only."""
    rows = conn.query(
        """
        SELECT date(o.created_at) AS day, l.sku, SUM(l.qty) AS units, SUM(l.qty * l.price_minor) AS revenue
        FROM orders o JOIN order_lines l ON l.order_id = o.id
        WHERE o.status IN ('paid', 'shipped')
        GROUP BY day, l.sku
        ORDER BY day, l.sku
        """
    )
    return to_csv(["day", "sku", "units", "revenue"],
                  [(r["day"], r["sku"], r["units"], money(r["revenue"])) for r in rows])


def orders_csv(conn):
    """One row per order with the customer's name."""
    rows = conn.query(
        """
        SELECT o.id, date(o.created_at) AS day, o.total_minor,
               CASE WHEN c.closed_at IS NULL THEN c.name ELSE '' END AS name
        FROM orders o JOIN customers c ON c.id = o.customer_id
        ORDER BY o.id
        """
    )
    return to_csv(["order_id", "date", "total", "customer_name"],
                  [(r["id"], r["day"], money(r["total_minor"]), r["name"]) for r in rows])
