# tests/adversarial/test_verification_attack.py — Adversarial Verification Attack Suite
from __future__ import annotations

from pathlib import Path
import pytest

from agent.verifier import ActionVerifier


def test_fake_file_creator_attack_caught(tmp_path):
    """Tool claims it wrote to disk, but file was never created."""
    fake_path = tmp_path / "never_created.txt"

    # Action claims success
    tool_output = f"Successfully wrote 500 lines to {fake_path}"

    res = ActionVerifier.verify_file_created(str(fake_path))
    assert res.verified is False
    assert res.error == "FILE_NOT_FOUND"


def test_empty_file_creator_attack_caught(tmp_path):
    """Tool creates 0-byte file but claims full success."""
    empty_path = tmp_path / "empty_corrupted.txt"
    empty_path.touch()

    res = ActionVerifier.verify_file_created(str(empty_path), min_size_bytes=10)
    assert res.verified is False
    assert res.error == "FILE_EMPTY"


def test_fake_process_launcher_attack_caught():
    """Tool claims it launched an application that is not in OS process table."""
    res = ActionVerifier.verify_process_running("non_existent_fake_daemon_99999")
    assert res.verified is False
    assert res.error == "PROCESS_NOT_FOUND"


def test_tool_output_error_masking_caught():
    """Tool returns string output with embedded error payload."""
    failing_outputs = [
        "ERROR: Access denied to remote host 192.168.1.5",
        "Traceback (most recent call last):\n  File 'test.py', line 1\nZeroDivisionError: division by zero",
        '{"status": "failure", "error": "Database connection refused"}',
        "PERMISSION DENIED: cannot modify /etc/shadow",
    ]

    for out in failing_outputs:
        res = ActionVerifier.verify_tool_output(out)
        assert res.verified is False, f"Verifier failed to catch error in output: '{out}'"
