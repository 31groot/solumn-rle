"""SQLite access with per-role grants.

    python db.py init      # (re)build data/shop.db from queries.sql + seed data + auth/roles.yaml

Every connection is opened for a service role. A statement that touches a table or view the
role has no grant for fails with PermissionDenied before it runs.
"""
import random
import sqlite3
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "shop.db"
ROLES_PATH = ROOT / "auth" / "roles.yaml"
WRITE_ACTIONS = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
SCHEMA_TABLES = {"sqlite_master", "sqlite_schema", "sqlite_temp_master"}


class PermissionDenied(Exception):
    pass


class RoleConnection:
    """A connection whose statements are checked against the role's grants."""

    def __init__(self, role, path=DB_PATH):
        self.role = role
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute("SELECT object, privilege FROM role_grants WHERE role = ?", (role,)).fetchall()
        if not rows:
            self.conn.close()
            raise PermissionDenied(f"unknown role {role!r}")
        groups = {}
        for g in self.conn.execute("SELECT grp, object FROM object_groups"):
            groups.setdefault(g["grp"], []).append(g["object"])
        self.grants = {(obj, r["privilege"]) for r in rows for obj in groups.get(r["object"], [r["object"]])}
        self._denied = None
        self.conn.set_authorizer(self._authorize)

    def _authorize(self, action, arg1, arg2, dbname, source):
        if action == sqlite3.SQLITE_READ:
            # Reads inside a view are allowed when the role may read the view itself.
            obj = source or arg1
            if arg1 in SCHEMA_TABLES or (obj, "read") in self.grants:
                return sqlite3.SQLITE_OK
            self._denied = ("read", arg1)
            return sqlite3.SQLITE_DENY
        if action in WRITE_ACTIONS:
            if (arg1, "write") in self.grants:
                return sqlite3.SQLITE_OK
            self._denied = ("write", arg1)
            return sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_TRANSACTION):
            return sqlite3.SQLITE_OK
        self._denied = ("run this statement on", arg1 or "the database")
        return sqlite3.SQLITE_DENY

    def query(self, sql, params=()):
        self._denied = None
        try:
            return self.conn.execute(sql, params).fetchall()
        except sqlite3.DatabaseError as e:
            if self._denied:
                verb, obj = self._denied
                raise PermissionDenied(f"role {self.role!r} may not {verb} {obj!r} (see auth/roles.yaml)") from e
            raise

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def connect(role, path=DB_PATH):
    return RoleConnection(role, path)


def load_grants(path=ROLES_PATH):
    roles = yaml.safe_load(Path(path).read_text())["roles"]
    return sorted({(role, obj, priv) for role, privs in roles.items()
                   for priv, objs in privs.items() for obj in objs})


def seed(conn):
    rng = random.Random(7)
    first = ["Asha", "Rohan", "Meera", "Karan", "Divya", "Imran", "Neha", "Arjun", "Sana", "Vikram"]
    last = ["Iyer", "Shah", "D'Souza", "Kapoor", "Nair", "Khan", "Rao", "Mehta"]
    closed = {9: "2026-10-20T09:00:00Z", 11: "2026-10-28T17:30:00Z"}
    customers = []
    for i in range(1, 21):
        name = f"{rng.choice(first)} {rng.choice(last)}"
        if i in (4, 13):
            name = {4: "Patel, Gupta & Co.", 13: 'Lakshmi "Lucky" Menon'}[i]
        customers.append((i, name, f"cust{i}@example.in", f"+91-98{rng.randint(10000000, 99999999)}",
                          f"{rng.randint(1, 200)} MG Road, Pune", closed.get(i)))
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)", customers)
    products = [("PEN-01", "Gel pen", 4500), ("NB-A5", "Notebook A5", 12999), ("LMP-3", "Desk lamp", 189900),
                ("HUB-C", "USB-C hub", 249950), ("MAT-2", "Desk mat", 79905)]
    conn.executemany("INSERT INTO products VALUES (?, ?, ?)", products)
    for oid in range(1001, 1046):
        lines = rng.sample(products, rng.randint(1, 3))
        qtys = [rng.randint(1, 4) for _ in lines]
        total = sum(p[2] * q for p, q in zip(lines, qtys))
        created = f"2026-10-{rng.randint(1, 31):02d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00Z"
        status = rng.choice(["paid", "paid", "shipped", "shipped", "refunded", "cancelled"])
        conn.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", (oid, rng.randint(1, 20), created, status, total))
        conn.executemany("INSERT INTO order_lines VALUES (?, ?, ?, ?)",
                         [(oid, p[0], q, p[2]) for p, q in zip(lines, qtys)])


def init(path=DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript((ROOT / "queries.sql").read_text())
    seed(conn)
    conn.executemany("INSERT INTO role_grants VALUES (?, ?, ?)", load_grants())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    if sys.argv[1:] != ["init"]:
        sys.exit(__doc__)
    init()
    print(f"initialised {DB_PATH}")
