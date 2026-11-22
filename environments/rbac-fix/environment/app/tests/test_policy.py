import subprocess
import sys

import pytest

from access import policy

APPROVED_ADMINS = ["dkaur", "priya.n"]


@pytest.fixture(scope="module")
def acl():
    return policy.load_acl()


def test_group_grants_its_roles(acl):
    assert "admin" in policy.effective_roles(acl, "dkaur")
    assert "billing-editor" in policy.effective_roles(acl, "bwright")


def test_user_roles_apply_without_groups(acl):
    assert policy.effective_roles(acl, "svc-ci") == {"deployer"}
    assert policy.is_allowed(acl, "svc-ci", "deploy:prod")


def test_inactive_and_unknown_users_have_no_access(acl):
    assert policy.effective_roles(acl, "tbose") == frozenset()
    assert not policy.is_allowed(acl, "tbose", "repo:read")
    assert not policy.is_allowed(acl, "nobody", "repo:read")


@pytest.mark.parametrize("grant,needed,ok", [
    ("*", "billing:write", True),
    ("repo:*", "repo:write", True),
    ("repo:read", "repo:read", True),
    ("repo:read", "repo:write", False),
    ("repo:*", "repository:read", False),
])
def test_grant_matching(grant, needed, ok):
    assert policy.grant_matches(grant, needed) is ok


def test_bad_permission_rejected(acl):
    with pytest.raises(policy.PolicyError):
        policy.is_allowed(acl, "dkaur", "repo")


def test_inherits_parent_group_roles(acl):
    assert {"analyst", "developer", "viewer"} <= policy.effective_roles(acl, "anika.s")
    assert policy.is_allowed(acl, "anika.s", "repo:read")
    assert policy.is_allowed(acl, "ylopez", "docs:read")
    assert policy.is_allowed(acl, "mchen", "dashboard:read")


def test_no_unexpected_admins(acl):
    assert policy.users_with_role(acl, "admin") == APPROVED_ADMINS


def test_cli_check_exit_codes():
    ok = subprocess.run([sys.executable, "-m", "access.cli", "check", "dkaur", "deploy:prod"],
                        capture_output=True, text=True)
    assert ok.returncode == 0 and ok.stdout.startswith("ALLOW")
    denied = subprocess.run([sys.executable, "-m", "access.cli", "check", "hsato", "billing:write"],
                            capture_output=True, text=True)
    assert denied.returncode == 1 and denied.stdout.startswith("DENY")
