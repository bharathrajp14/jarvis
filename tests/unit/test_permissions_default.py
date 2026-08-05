"""Test default permission policy mode is CONFIRM_DESTRUCTIVE when unconfigured."""
import os
from permissions import _normalize_mode, PermissionMode, PermissionPolicy, DESTRUCTIVE_TOOLS


def test_permission_default_fallback():
    assert _normalize_mode(None) == PermissionMode.CONFIRM_DESTRUCTIVE
    assert _normalize_mode("") == PermissionMode.CONFIRM_DESTRUCTIVE
    assert _normalize_mode("invalid_mode") == PermissionMode.CONFIRM_DESTRUCTIVE


def test_permission_policy_blocks_destructive_by_default():
    policy = PermissionPolicy()
    assert policy.mode == PermissionMode.CONFIRM_DESTRUCTIVE

    # Safe tools should pass
    assert policy.check("file_read") is True
    assert policy.check("web_search") is True

    # Destructive tools must be blocked (return False)
    assert policy.check("run_code") is False
    assert policy.check("file_delete") is False
    assert policy.check("process_kill") is False
