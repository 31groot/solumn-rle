"""Drive the workspace app in-process and print what happened as JSON.

sqlite3.connect is wrapped so every connection records whether the app installed an authorizer and
which tables it read; db.connect is wrapped to record the role each connection was opened for.
"""
import json
import os
import sqlite3
import sys

APP = sys.argv[1]
sys.path.insert(0, APP)
os.chdir(APP)
reads, roles, out = [], [], {}
_real_connect = sqlite3.connect


class Tracked(sqlite3.Connection):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._app_auth = None
        super().set_authorizer(self._monitor)

    def _monitor(self, action, arg1, arg2, dbname, source):
        if action == sqlite3.SQLITE_READ and arg1 == "customers":
            reads.append({"guarded": self._app_auth is not None, "via": source})
        if self._app_auth is None:
            return sqlite3.SQLITE_OK
        return self._app_auth(action, arg1, arg2, dbname, source)

    def set_authorizer(self, fn):
        self._app_auth = fn


def tracked_connect(*a, **k):
    k["factory"] = Tracked
    return _real_connect(*a, **k)


sqlite3.connect = tracked_connect
try:
    import db
    _db_connect = db.connect

    def role_connect(*a, **k):
        roles.append(k.get("role", a[0] if a else None))
        return _db_connect(*a, **k)

    db.connect = role_connect
    from app import app
    client = app.test_client()

    def get(path):
        r = client.get(path)
        return {"status": r.status_code, "mimetype": r.mimetype, "body": r.get_data(as_text=True)}

    reads.clear(); roles.clear()
    out["export"] = get("/export/orders.csv")
    out["export_roles"] = sorted({str(r) for r in roles})
    out["export_customer_reads"] = list(reads)
    out["regression"] = {p: get(p) for p in ["/health", "/orders/1001", "/orders/1044", "/orders?status=refunded",
                                             "/customers/4", "/customers/13", "/customers/999",
                                             "/export/daily_sales.csv"]}
    try:
        with _db_connect("export_service") as conn:
            conn.query("SELECT name FROM customers LIMIT 1")
        out["export_service_reads_customers"] = True
    except Exception as e:  # noqa: BLE001
        out["export_service_reads_customers"] = False
        out["export_service_denial"] = f"{type(e).__name__}: {e}"
except Exception as e:  # noqa: BLE001
    out["error"] = f"{type(e).__name__}: {e}"
print(json.dumps(out))
