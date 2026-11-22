"""Access policy evaluation for the internal ACL.

The ACL lives in data/acl.json (override with ACL_PATH or --acl). It defines roles (sets of
permissions), groups (which grant roles and can inherit from parent groups) and users.
How a user's effective roles are worked out is described in access/README.md.

Permissions are "<resource>:<action>" strings. A grant may use "*" as the action
("repo:*") or on its own ("*") to match everything.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import groups as groupmod

DEFAULT_ACL = Path(__file__).resolve().parent.parent / "data" / "acl.json"


class PolicyError(ValueError):
    """The ACL file or a permission string is malformed."""


@dataclass(frozen=True)
class Role:
    name: str
    permissions: tuple
    privileged: bool = False


@dataclass(frozen=True)
class User:
    name: str
    active: bool
    roles: tuple
    groups: tuple
    last_login: str = ""


@dataclass
class Acl:
    roles: dict
    groups: dict
    users: dict
    path: Path = None


def acl_path(path=None):
    return Path(path or os.environ.get("ACL_PATH") or DEFAULT_ACL)


def read_raw(path=None):
    p = acl_path(path)
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise PolicyError(f"cannot read ACL {p}: {e}") from e


def write_raw(raw, path=None):
    """Write the ACL back with one record per line, so diffs stay reviewable."""
    parts = []
    for key, value in raw.items():
        if isinstance(value, dict):
            rows = ",\n".join(f"    {json.dumps(k)}: {json.dumps(v)}" for k, v in value.items())
            parts.append(f"  {json.dumps(key)}: {{\n{rows}\n  }}")
        else:
            parts.append(f"  {json.dumps(key)}: {json.dumps(value)}")
    acl_path(path).write_text("{\n" + ",\n".join(parts) + "\n}\n")


def _str_list(value, where):
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise PolicyError(f"{where} must be a list of strings")
    return tuple(value)


def parse_acl(raw, path=None):
    if not isinstance(raw, dict):
        raise PolicyError("ACL must be a JSON object")
    roles = {}
    for name, spec in raw.get("roles", {}).items():
        perms = _str_list(spec.get("permissions", []), f"role {name!r} permissions")
        for p in perms:
            if p != "*" and p.count(":") != 1:
                raise PolicyError(f"role {name!r}: bad permission {p!r}")
        roles[name] = Role(name, perms, spec.get("privileged", False) is True)
    try:
        groups = groupmod.parse_groups(raw.get("groups", {}))
    except groupmod.GroupError as e:
        raise PolicyError(str(e)) from e
    users = {}
    for name, spec in raw.get("users", {}).items():
        users[name] = User(
            name=name,
            active=spec.get("active", True) is True,
            roles=_str_list(spec.get("roles", []), f"user {name!r} roles"),
            groups=_str_list(spec.get("groups", []), f"user {name!r} groups"),
            last_login=spec.get("last_login", ""),
        )
    return Acl(roles, groups, users, path)


def load_acl(path=None):
    p = acl_path(path)
    return parse_acl(read_raw(p), p)


def effective_roles(acl, username):
    """Names of the roles `username` holds. Inactive and unknown users hold none."""
    user = acl.users.get(username)
    if user is None or not user.active:
        return frozenset()
    found = set(user.roles)
    for name in user.groups:
        if name in acl.groups:
            for g in (name, *groupmod.ancestors(acl.groups, name)):
                found.update(acl.groups[g].roles)
    return frozenset(r for r in found if r in acl.roles)


def permissions_for(acl, username):
    return frozenset(p for r in effective_roles(acl, username) for p in acl.roles[r].permissions)


def grant_matches(grant, needed):
    if grant == "*":
        return True
    g_res, _, g_act = grant.partition(":")
    n_res, _, n_act = needed.partition(":")
    return g_res == n_res and g_act in ("*", n_act)


def is_allowed(acl, username, permission):
    if permission.count(":") != 1:
        raise PolicyError(f"bad permission {permission!r}, expected <resource>:<action>")
    return any(grant_matches(g, permission) for g in permissions_for(acl, username))


def users_with_role(acl, role):
    return sorted(u for u in acl.users if role in effective_roles(acl, u))


def privileged_roles(acl, username):
    return sorted(r for r in effective_roles(acl, username) if acl.roles[r].privileged)
