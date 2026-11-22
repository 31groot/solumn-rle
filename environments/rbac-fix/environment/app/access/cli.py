"""Command-line access tool.

  python -m access.cli roles <user>             effective roles
  python -m access.cli check <user> <perm>      ALLOW / DENY (exit 0 / 1)
  python -m access.cli who <role>               users holding a role
  python -m access.cli tree <group>             a group and its ancestors
  python -m access.cli lint                     broken references and cycles in the ACL
  python -m access.cli deactivate <user> --reason TEXT
  python -m access.cli reactivate <user> --reason TEXT
  python -m access.cli audit [--user NAME]      show the audit log
"""
import argparse
import sys

from . import audit, groups, policy


def cmd_roles(acl, args):
    roles = sorted(policy.effective_roles(acl, args.user))
    print(", ".join(roles) if roles else "(none)")
    return 0


def cmd_check(acl, args):
    ok = policy.is_allowed(acl, args.user, args.permission)
    print(f"{'ALLOW' if ok else 'DENY'} {args.user} {args.permission}")
    return 0 if ok else 1


def cmd_who(acl, args):
    if args.role not in acl.roles:
        print(f"unknown role {args.role!r}", file=sys.stderr)
        return 2
    for name in policy.users_with_role(acl, args.role):
        print(name)
    return 0


def cmd_tree(acl, args):
    if args.group not in acl.groups:
        print(f"unknown group {args.group!r}", file=sys.stderr)
        return 2
    for name in [args.group] + groups.ancestors(acl.groups, args.group):
        g = acl.groups[name]
        print(f"{name}: {', '.join(g.roles) or '-'}")
    return 0


def cmd_lint(acl, args):
    problems = []
    for g in acl.groups.values():
        problems += [f"group {g.name}: undefined parent {p}" for p in g.parents if p not in acl.groups]
        problems += [f"group {g.name}: undefined role {r}" for r in g.roles if r not in acl.roles]
    for u in acl.users.values():
        problems += [f"user {u.name}: undefined group {g}" for g in u.groups if g not in acl.groups]
        problems += [f"user {u.name}: undefined role {r}" for r in u.roles if r not in acl.roles]
    problems += [f"cycle: {child} -> {parent}" for child, parent in groups.find_cycles(acl.groups)]
    print("\n".join(problems) if problems else "ok")
    return 1 if problems else 0


def cmd_audit(acl, args):
    for e in audit.read(target=args.user):
        print(f"{e['ts']}  {e['actor']:<10} {e['action']:<10} {e['target']:<10} {e.get('reason', '')}")
    return 0


def set_active(args, active):
    if not args.reason.strip():
        print("--reason must not be empty", file=sys.stderr)
        return 2
    raw = policy.read_raw(args.acl)
    user = raw.get("users", {}).get(args.user)
    if user is None:
        print(f"unknown user {args.user!r}", file=sys.stderr)
        return 2
    state = "active" if active else "inactive"
    if user.get("active", True) is active:
        print(f"{args.user} is already {state}")
        return 0
    user["active"] = active
    policy.write_raw(raw, args.acl)
    audit.record("reactivate" if active else "deactivate", args.user, args.reason, actor=args.actor)
    print(f"{args.user} is now {state}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="access", description="Inspect and administer the ACL.")
    parser.add_argument("--acl", help="ACL file (default: $ACL_PATH or data/acl.json)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("roles")
    p.add_argument("user")
    p.set_defaults(func=cmd_roles)
    p = sub.add_parser("check")
    p.add_argument("user")
    p.add_argument("permission")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("who")
    p.add_argument("role")
    p.set_defaults(func=cmd_who)
    p = sub.add_parser("tree")
    p.add_argument("group")
    p.set_defaults(func=cmd_tree)
    sub.add_parser("lint").set_defaults(func=cmd_lint)
    p = sub.add_parser("audit")
    p.add_argument("--user")
    p.set_defaults(func=cmd_audit)
    for name in ("deactivate", "reactivate"):
        p = sub.add_parser(name)
        p.add_argument("user")
        p.add_argument("--reason", required=True)
        p.add_argument("--actor", help="who is making the change (default: login name)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.cmd in ("deactivate", "reactivate"):
            return set_active(args, args.cmd == "reactivate")
        return args.func(policy.load_acl(args.acl), args)
    except (policy.PolicyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
