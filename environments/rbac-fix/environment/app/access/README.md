# access

Works out who can do what in our internal tools, from the ACL in `data/acl.json`.
Owner: Priya Nair (access). Tickets go in the ACC project.

## ACL file

```
roles:  name -> {"permissions": [...], "privileged": true|false}
groups: name -> {"roles": [...], "parents": [...], "description": "..."}
users:  name -> {"active": true|false, "roles": [...], "groups": [...], "last_login": "YYYY-MM-DD"}
```

Permissions are `<resource>:<action>` strings, e.g. `repo:read`. A grant can use `<resource>:*`
for every action on a resource, or `*` for everything. Roles marked `"privileged": true`
(`admin`, `security-admin`) are the ones covered by the quarterly access review.

## Effective roles

1. Inactive users (`"active": false`) and unknown users have no roles.
2. A user's own `roles` apply.
3. Each group in the user's `groups` grants its `roles`.
4. Groups inherit: a group also grants the roles of each of its `parents`, and of their
   parents, all the way up. A group reached by more than one path counts once, and cycles
   in `parents` are tolerated.
5. Roles and groups that are referenced but not defined are ignored.

A user's permissions are the union of the permissions of their effective roles.

## Python API

```python
from access import policy
acl = policy.load_acl()                 # data/acl.json, or $ACL_PATH
policy.effective_roles(acl, "anika.s")  # frozenset of role names
policy.is_allowed(acl, "anika.s", "repo:read")
policy.users_with_role(acl, "admin")    # sorted user names
```

## CLI

```
python -m access.cli roles <user>
python -m access.cli check <user> <permission>     # exit 0 = ALLOW, 1 = DENY
python -m access.cli who <role>
python -m access.cli tree <group>
python -m access.cli lint
python -m access.cli deactivate <user> --reason "..."
python -m access.cli reactivate <user> --reason "..."
python -m access.cli audit [--user <name>]
```

`--acl <file>` points any command at another ACL file.

## Audit log

`deactivate` and `reactivate` append an event (time, actor, action, target, reason) to
`data/audit.jsonl` (override with `AUDIT_LOG`). The log is append-only.

## Tests

Run `python -m pytest` from the repo root.
