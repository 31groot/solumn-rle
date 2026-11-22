"""Group records from the ACL file and helpers for walking the group graph."""
from collections import deque
from dataclasses import dataclass

FIELDS = {"roles", "parents", "description"}


class GroupError(ValueError):
    """A group record is malformed."""


@dataclass(frozen=True)
class Group:
    name: str
    roles: tuple = ()
    parents: tuple = ()
    description: str = ""


def _names(value, where):
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise GroupError(f"{where} must be a list of names")
    return tuple(value)


def parse_groups(raw):
    if not isinstance(raw, dict):
        raise GroupError("groups must be a JSON object")
    out = {}
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            raise GroupError(f"group {name!r} must be an object")
        unknown = set(spec) - FIELDS
        if unknown:
            raise GroupError(f"group {name!r}: unknown field(s) {sorted(unknown)}")
        out[name] = Group(
            name=name,
            roles=_names(spec.get("roles", []), f"group {name!r} roles"),
            parents=_names(spec.get("parents", []), f"group {name!r} parents"),
            description=spec.get("description", ""),
        )
    return out


def ancestors(groups, name):
    """Groups reachable from `name` through `parents`, nearest first, each listed once.

    Parents that are not defined are skipped; cycles are tolerated.
    """
    order, seen = [], {name}
    queue = deque(groups[name].parents if name in groups else ())
    while queue:
        g = queue.popleft()
        if g in seen or g not in groups:
            continue
        seen.add(g)
        order.append(g)
        queue.extend(groups[g].parents)
    return order


def members(users, group):
    """Names of users listed directly in `group`."""
    return sorted(u.name for u in users.values() if group in u.groups)


def find_cycles(groups):
    """Parent links that close a cycle, as (child, parent) pairs."""
    return [(g.name, p) for g in groups.values() for p in g.parents
            if p == g.name or g.name in ancestors(groups, p)]
