"""SQLite product store. Newest ``updated_at`` wins, for products and deletions alike."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    sku         TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    price_minor INTEGER NOT NULL,
    currency    TEXT NOT NULL,
    stock       INTEGER NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tombstones (
    sku        TEXT PRIMARY KEY,
    deleted_at TEXT NOT NULL
);
"""

COLUMNS = ("sku", "title", "price_minor", "currency", "stock", "updated_at")


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()

    def _scalar(self, sql, *args):
        row = self.conn.execute(sql, args).fetchone()
        return row[0] if row else None

    def upsert(self, product):
        """Insert or update a product row. Returns False if a newer state is already stored."""
        sku, ts = product["sku"], product["updated_at"]
        current = self._scalar("SELECT updated_at FROM products WHERE sku = ?", sku)
        deleted = self._scalar("SELECT deleted_at FROM tombstones WHERE sku = ?", sku)
        if (current is not None and current >= ts) or (deleted is not None and deleted >= ts):
            return False
        self.conn.execute(
            f"INSERT OR REPLACE INTO products ({', '.join(COLUMNS)}) VALUES (?, ?, ?, ?, ?, ?)",
            tuple(product[c] for c in COLUMNS),
        )
        self.conn.execute("DELETE FROM tombstones WHERE sku = ?", (sku,))
        return True

    def delete(self, sku, deleted_at):
        """Apply a tombstone. Returns False if the stored product (or tombstone) is newer."""
        current = self._scalar("SELECT updated_at FROM products WHERE sku = ?", sku)
        known = self._scalar("SELECT deleted_at FROM tombstones WHERE sku = ?", sku)
        if (current is not None and current >= deleted_at) or (known is not None and known >= deleted_at):
            return False
        self.conn.execute("DELETE FROM products WHERE sku = ?", (sku,))
        self.conn.execute("INSERT OR REPLACE INTO tombstones (sku, deleted_at) VALUES (?, ?)", (sku, deleted_at))
        return current is not None

    def get(self, sku):
        row = self.conn.execute(f"SELECT {', '.join(COLUMNS)} FROM products WHERE sku = ?", (sku,)).fetchone()
        return dict(zip(COLUMNS, row)) if row else None

    def all_products(self):
        rows = self.conn.execute(f"SELECT {', '.join(COLUMNS)} FROM products ORDER BY sku").fetchall()
        return [dict(zip(COLUMNS, r)) for r in rows]

    def count(self):
        return self._scalar("SELECT COUNT(*) FROM products")

    def commit(self):
        self.conn.commit()
