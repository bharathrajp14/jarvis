# tests/test_flaw_remediations_v2.py — Verification Tests for Empirical Codebase Flaw Fixes
import pytest
from permissions import check_permission, PathPolicy, PathTier
from watchers.file_watcher import FileWatcher
from watchers.system_watcher import SystemWatcher


def test_permissions_path_policy_enforcement():
    # 1. Normal workspace path check (should be permitted)
    assert check_permission("view_file", {"AbsolutePath": "d:/BRJARVIS/Br-Jarvis/main.py"}) is True

    # 2. Restricted TIER_2 path check (should be blocked by check_permission)
    assert check_permission("view_file", {"AbsolutePath": "C:/Windows/System32/config/SAM"}) is False
    assert check_permission("view_file", {"AbsolutePath": "C:/Users/user/.ssh/id_rsa"}) is False


def test_file_watcher_recursive_scope():
    watcher = FileWatcher()
    assert hasattr(watcher, "scan_for_changes")
    # Execute scan without raising errors
    changes = watcher.scan_for_changes()
    assert isinstance(changes, int)


def test_system_watcher_warmup():
    watcher = SystemWatcher()
    telemetry = watcher.check_telemetry()
    assert "timestamp" in telemetry
    assert telemetry["status"] == "nominal"
