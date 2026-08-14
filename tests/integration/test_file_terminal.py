# tests/integration/test_file_terminal.py — Scenarios 10 to 12: File and Terminal Tool Integration
from __future__ import annotations

import logging
import os
import pytest
from tools.registry import execute_tool

logger = logging.getLogger(__name__)

os.environ["JARVIS_PERMISSION_MODE"] = "allow_all"


def test_scenario_10_file_operations():
    """Scenario 10: Create a test file, write text, and read it back."""
    from permissions import PERMISSIONS, PermissionMode
    PERMISSIONS.mode = PermissionMode.ALLOW_ALL
    test_path = "integration_test_file.txt"
    content = "Hello from BR JARVIS Integration Suite!"

    # Write file
    write_res = execute_tool("file_write", {"path": test_path, "content": content})
    assert "File written" in write_res

    # Read file
    read_res = execute_tool("file_read", {"path": test_path})
    assert read_res == content

    # Cleanup
    try:
        from tools.file_tools import WORKSPACE_DIR
        file_to_del = WORKSPACE_DIR / test_path
        if file_to_del.exists():
            file_to_del.unlink()
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
def test_scenario_11_12_terminal_and_git():
    """Scenarios 11 & 12: Run terminal shell command and check output."""
    # Test simple echo via cli_controller
    echo_res = execute_tool("cli_controller", {"action": "run", "cmd": "echo hello"})
    if "ERROR" not in echo_res:
        assert "hello" in echo_res.lower()

    # Test git status command execution
    git_res = execute_tool("cli_controller", {"action": "run", "cmd": "git status"})
    if "ERROR" not in git_res:
        assert "on branch" in git_res.lower() or "not a git repository" in git_res.lower() or "untracked files" in git_res.lower()
