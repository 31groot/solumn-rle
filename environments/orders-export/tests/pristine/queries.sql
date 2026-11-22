-- Schema for the shop database. Applied by `python db.py init`.

CREATE TABLE customers (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    phone      TEXT,
    address    TEXT,
    closed_at  TEXT                       -- UTC; NULL while the account is open
);

CREATE TABLE products (
    sku         TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    price_minor INTEGER NOT NULL
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    created_at  TEXT NOT NULL,            -- UTC, ISO 8601 with Z
    status      TEXT NOT NULL CHECK (status IN ('paid', 'shipped', 'refunded', 'cancelled')),
    total_minor INTEGER NOT NULL          -- sum of order_lines, in paise
);

CREATE TABLE order_lines (
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    sku         TEXT NOT NULL REFERENCES products(sku),
    qty         INTEGER NOT NULL CHECK (qty > 0),
    price_minor INTEGER NOT NULL,
    PRIMARY KEY (order_id, sku)
);

CREATE INDEX orders_by_customer ON orders(customer_id);
CREATE INDEX orders_by_created ON orders(created_at);

-- Access control: one row per (role, object, privilege). Loaded from auth/roles.yaml.
CREATE TABLE role_grants (
    role      TEXT NOT NULL,
    object    TEXT NOT NULL,
    privilege TEXT NOT NULL CHECK (privilege IN ('read', 'write')),
    PRIMARY KEY (role, object, privilege)
);

-- Named groups of objects that roles.yaml can grant as one unit.
CREATE TABLE object_groups (
    grp    TEXT NOT NULL,
    object TEXT NOT NULL,
    PRIMARY KEY (grp, object)
);

-- Daily totals for the reporting dashboards.
CREATE VIEW rpt_daily_totals_v AS
SELECT date(created_at)                      AS day,
       COUNT(*)                              AS orders,
       SUM(total_minor)                      AS revenue_minor
FROM orders
WHERE status IN ('paid', 'shipped')
GROUP BY date(created_at);

-- Order-level reporting rows (FIN-88).
CREATE VIEW rpt_order_lines_v AS
SELECT o.id                                  AS order_id,
       date(o.created_at)                    AS order_date,
       printf('%.2f', o.total_minor / 100.0) AS total,
       c.name                                AS customer_name
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE c.closed_at IS NULL;

-- Units sold per product, all time.
CREATE VIEW rpt_product_sales_v AS
SELECT l.sku, p.title, SUM(l.qty) AS units, SUM(l.qty * l.price_minor) AS revenue_minor
FROM order_lines l
JOIN products p ON p.sku = l.sku
JOIN orders o ON o.id = l.order_id
WHERE o.status IN ('paid', 'shipped')
GROUP BY l.sku;

INSERT INTO object_groups (grp, object) VALUES
    ('reporting_views', 'rpt_daily_totals_v'),
    ('reporting_views', 'rpt_order_lines_v'),
    ('reporting_views', 'rpt_product_sales_v');
