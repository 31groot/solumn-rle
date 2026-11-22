"""Run policy queries against the access package in APP_DIR.

usage: python -I case_runner.py APP_DIR < {"acl": {...}, "cases": [...]}
Prints one JSON list (one {"result": ...} or {"exception": ...} per case) as the last line.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
req = json.loads(sys.stdin.read())
n = len(req["cases"])
try:
    from access import policy

    path = Path(tempfile.mkdtemp()) / "acl.json"
    path.write_text(json.dumps(req["acl"]))
    acl = policy.load_acl(path)
except Exception as e:  # noqa: BLE001 - an unloadable package/ACL fails every case
    print(json.dumps([{"exception": f"load failed: {type(e).__name__}: {e}"}] * n))
    sys.exit(0)

out = []
for c in req["cases"]:
    try:
        if c["op"] == "roles":
            r = sorted(policy.effective_roles(acl, c["user"]))
        elif c["op"] == "allowed":
            r = bool(policy.is_allowed(acl, c["user"], c["perm"]))
        elif c["op"] == "who":
            r = list(policy.users_with_role(acl, c["role"]))
        else:
            raise ValueError(f"unknown op {c['op']}")
        out.append({"result": r})
    except Exception as e:  # noqa: BLE001
        out.append({"exception": f"{type(e).__name__}: {e}"})
print(json.dumps(out))
