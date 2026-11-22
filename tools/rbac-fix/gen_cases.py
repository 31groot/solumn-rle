#!/usr/bin/env python3
"""Write environments/rbac-fix/tests/cases.json and the pristine copies.

Expectations are written by hand from access/README.md (rules 1-5), then checked against the safe
reference and the shipped (buggy) code. usage: tools/rbac-fix/gen_cases.py [python-with-pytest]
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENV = Path(__file__).resolve().parents[2] / "environments" / "rbac-fix"
APP = ENV / "environment" / "app"
TESTS = ENV / "tests"
PY = sys.argv[1] if len(sys.argv) > 1 else sys.executable

R = {
    "admin": {"privileged": True, "permissions": ["*"]},
    "sec": {"privileged": True, "permissions": ["iam:*"]},
    "dev": {"permissions": ["repo:read", "repo:write"]},
    "view": {"permissions": ["docs:read"]},
    "ops": {"permissions": ["deploy:prod"]},
}


def u(groups=(), roles=(), active=True):
    return {"active": active, "roles": list(roles), "groups": list(groups)}


ACLS = {
    "chain": {"roles": R, "groups": {
        "a": {"roles": ["view"]}, "b": {"roles": ["dev"], "parents": ["a"]},
        "c": {"roles": ["ops"], "parents": ["b"]}},
        "users": {"u_c": u(["c"]), "u_b": u(["b"]), "u_off": u(["c"], active=False),
                  "u_direct": u(["b"], ["ops"])}},
    "diamond": {"roles": R, "groups": {
        "top": {"roles": ["view"]}, "left": {"roles": ["dev"], "parents": ["top"]},
        "right": {"roles": ["ops"], "parents": ["top"]}, "bottom": {"parents": ["left", "right"]}},
        "users": {"u": u(["bottom"])}},
    "cycle": {"roles": R, "groups": {
        "x": {"roles": ["dev"], "parents": ["y"]}, "y": {"roles": ["view"], "parents": ["x"]}},
        "users": {"u_x": u(["x"]), "u_y": u(["y"])}},
    "selfcycle": {"roles": R, "groups": {"z": {"roles": ["dev"], "parents": ["z"]}},
        "users": {"u": u(["z"])}},
    "deep": {"roles": R, "groups": {"l0": {"roles": ["view"]}, **{f"l{i}": {"parents": [f"l{i - 1}"]}
                                                                    for i in range(1, 8)}},
        "users": {"u": u(["l7"])}},
    "missing": {"roles": R, "groups": {
        "g": {"roles": ["dev", "nope"], "parents": ["ghost", "base"]}, "base": {"roles": ["view"]}},
        "users": {"u": u(["g", "nogroup"])}},
    "priv": {"roles": R, "groups": {
        "admins": {"roles": ["admin"]}, "base": {"roles": ["view"]},
        "oncall": {"roles": ["ops"], "parents": ["admins", "base"]},
        "child": {"roles": ["dev"], "parents": ["oncall"]}, "team": {"parents": ["admins"]},
        "secteam": {"roles": ["sec"], "parents": ["base"]}},
        "users": {"u_oncall": u(["oncall"]), "u_child": u(["child"]), "u_team": u(["team"]),
                  "u_sec": u(["secteam"]), "u_both": u(["child", "team"]),
                  "u_off": u(["child"], active=False)}},
    "flat": {"roles": R, "groups": {
        "admins": {"roles": ["admin"]}, "devs": {"roles": ["dev"]}, "readers": {"roles": ["view"]}},
        "users": {"f_admin": u(["admins"]), "f_dev": u(["devs", "readers"]), "f_none": u(),
                  "f_read": u(["readers"]), "f_roles": u([], ["ops", "undefined"])}},
}


def roles(i, acl, user, exp):
    return {"id": i, "acl": acl, "op": "roles", "user": user, "expect": sorted(exp)}


def allowed(i, acl, user, perm, exp):
    return {"id": i, "acl": acl, "op": "allowed", "user": user, "perm": perm, "expect": exp}


def who(i, acl, role, exp):
    return {"id": i, "acl": acl, "op": "who", "role": role, "expect": exp}


DDV = ["deployer", "developer", "viewer"]
FUNCTIONAL = [
    roles("chain_grandparent", "chain", "u_c", ["dev", "ops", "view"]),
    roles("chain_parent", "chain", "u_b", ["dev", "view"]),
    allowed("chain_inherited_permission", "chain", "u_c", "docs:read", True),
    roles("inactive_user_inherits_nothing", "chain", "u_off", []),
    roles("direct_roles_plus_inherited", "chain", "u_direct", ["dev", "ops", "view"]),
    roles("diamond_counts_once", "diamond", "u", ["dev", "ops", "view"]),
    roles("cycle_tolerated_x", "cycle", "u_x", ["dev", "view"]),
    roles("cycle_tolerated_y", "cycle", "u_y", ["dev", "view"]),
    roles("undefined_parent_and_role_ignored", "missing", "u", ["dev", "view"]),
    roles("self_parent_tolerated", "selfcycle", "u", ["dev"]),
    roles("deep_chain_seven_levels", "deep", "u", ["view"]),
    allowed("deep_chain_permission", "deep", "u", "docs:read", True),
    roles("privileged_role_inherited", "priv", "u_oncall", ["admin", "ops", "view"]),
    roles("privileged_role_inherited_two_levels", "priv", "u_child", ["admin", "dev", "ops", "view"]),
    roles("roleless_group_passes_parent_roles", "priv", "u_team", ["admin"]),
    roles("second_privileged_role_inherited_not_admin", "priv", "u_sec", ["sec", "view"]),
    roles("overlapping_groups_union", "priv", "u_both", ["admin", "dev", "ops", "view"]),
    roles("inactive_user_no_inherited_admin", "priv", "u_off", []),
    allowed("inherited_wildcard_permission", "priv", "u_child", "billing:write", True),
    allowed("inherited_nonwildcard_denied", "priv", "u_sec", "repo:read", False),
    who("who_admin_includes_inherited", "priv", "admin", ["u_both", "u_child", "u_oncall", "u_team"]),
    # shipped data
    roles("acl_priya", "pristine", "priya.n", ["admin", "deployer", "developer", "security-admin", "viewer"]),
    roles("acl_dkaur", "pristine", "dkaur", ["admin", *DDV]),
    roles("acl_rohan", "pristine", "rohan.k", ["developer", "viewer"]),
    roles("acl_anika", "pristine", "anika.s", ["analyst", "developer", "viewer"]),
    roles("acl_ines", "pristine", "ines.d", ["analyst", "developer", "viewer"]),
    roles("acl_mchen", "pristine", "mchen", DDV),
    roles("acl_okafor", "pristine", "okafor", ["billing-editor", "developer", "viewer"]),
    roles("acl_bwright", "pristine", "bwright", ["billing-editor", "viewer"]),
    roles("acl_ylopez", "pristine", "ylopez", ["support-agent", "viewer"]),
    roles("acl_rgupta", "pristine", "rgupta", ["security-admin", "viewer"]),
    roles("acl_jmehta", "pristine", "jmehta", ["admin", *DDV]),
    roles("acl_kfoster", "pristine", "kfoster", ["admin", *DDV]),
    roles("acl_lwu", "pristine", "lwu", ["admin", *DDV]),
    allowed("acl_anika_repo_read", "pristine", "anika.s", "repo:read", True),
    allowed("acl_jmehta_inherited_wildcard", "pristine", "jmehta", "iam:write", True),
    who("acl_who_admin", "pristine", "admin", ["dkaur", "jmehta", "kfoster", "lwu", "priya.n"]),
    who("acl_who_security_admin", "pristine", "security-admin", ["priya.n", "rgupta"]),
]
REGRESSION = [
    roles("acl_hsato", "pristine", "hsato", ["viewer"]),
    roles("acl_svc_ci", "pristine", "svc-ci", ["deployer"]),
    roles("acl_tbose_inactive", "pristine", "tbose", []),
    roles("acl_unknown_user", "pristine", "nobody", []),
    allowed("acl_hsato_no_billing", "pristine", "hsato", "billing:write", False),
    allowed("acl_dkaur_wildcard", "pristine", "dkaur", "anything:at-all", True),
    roles("flat_admin", "flat", "f_admin", ["admin"]),
    roles("flat_two_groups", "flat", "f_dev", ["dev", "view"]),
    roles("flat_no_groups", "flat", "f_none", []),
    roles("flat_single_group", "flat", "f_read", ["view"]),
    roles("flat_undefined_role_ignored", "flat", "f_roles", ["ops"]),
    allowed("flat_resource_wildcard", "flat", "f_dev", "repo:write", True),
    allowed("flat_other_resource_denied", "flat", "f_dev", "deploy:prod", False),
    who("flat_who_view", "flat", "view", ["f_dev", "f_read"]),
]


def run(app, cases, pristine):
    out = []
    for name in dict.fromkeys(c["acl"] for c in cases):
        batch = [c for c in cases if c["acl"] == name]
        raw = pristine if name == "pristine" else ACLS[name]
        r = subprocess.run([sys.executable, "-I", str(TESTS / "case_runner.py"), str(app)],
                           input=json.dumps({"acl": raw, "cases": batch}), capture_output=True, text=True)
        out += [(c, g) for c, g in zip(batch, json.loads(r.stdout.splitlines()[-1]))]
    return [c["id"] for c, g in out if g.get("result") != c["expect"]]


def main():
    pristine_dir = TESTS / "pristine"
    pristine_dir.mkdir(exist_ok=True)
    shutil.copy(APP / "data" / "acl.json", pristine_dir / "acl.json")
    shutil.copy(APP / "tests" / "test_policy.py", pristine_dir / "test_policy.py")
    collected = subprocess.run([PY, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                                "tests/test_policy.py"], cwd=APP, capture_output=True, text=True).stdout
    ids = [line.split("::", 1)[1] for line in collected.splitlines() if "::" in line]
    assert len(ids) == 12, collected
    (TESTS / "cases.json").write_text(json.dumps(
        {"acls": ACLS, "functional": FUNCTIONAL, "regression": REGRESSION, "visible_test_ids": ids}, indent=1))

    pristine = json.loads((pristine_dir / "acl.json").read_text())
    safe = Path(tempfile.mkdtemp())
    shutil.copytree(APP / "access", safe / "access")
    shutil.copy(ENV / "solution" / "src" / "policy.py", safe / "access" / "policy.py")
    bad = run(safe, FUNCTIONAL + REGRESSION, pristine)
    assert not bad, f"safe reference fails: {bad}"
    shipped_f, shipped_r = run(APP, FUNCTIONAL, pristine), run(APP, REGRESSION, pristine)
    assert shipped_f and not shipped_r, (shipped_f, shipped_r)
    print(f"cases.json: {len(FUNCTIONAL)} functional, {len(REGRESSION)} regression, {len(ids)} visible ids. "
          f"safe ref passes all; shipped code fails {len(shipped_f)} functional, 0 regression.")


if __name__ == "__main__":
    main()
