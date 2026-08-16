"""
Test 38 — Retry Preserves Completed Steps — MK40.2 §8

Verifies that when a task is retried after a step 2 failure, step 1 (already
verified in the ledger) is NOT re-executed. Only failed steps are retried.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


@pytest.fixture
def executor():
    """Create an AgentExecutor with a minimal config."""
    from brjarvis.agent.executor import AgentExecutor
    return AgentExecutor()


@pytest.mark.unit
def test_retry_skips_already_verified_steps(tmp_path):
    """
    MK40.2 Test 38: When step 1 is verified in the ledger and the executor
    runs a second attempt (replan), step 1 must NOT be re-executed.
    """
    from brjarvis.agent.execution_ledger import ExecutionLedger, LedgerEntry, LedgerStatus
    from brjarvis.memory.canonical_db import CanonicalDatabaseManager
    from brjarvis.agent.executor import AgentExecutor

    # Set up a ledger with step 1 already verified
    db = CanonicalDatabaseManager(db_path=tmp_path / "test.db")
    ledger = ExecutionLedger(db_manager=db)
    ledger.append(LedgerEntry(
        tool_name="file_write",
        task_id="retry_task",
        step_id="step_1",
        status=LedgerStatus.SUCCESS,
        verification_status=LedgerStatus.SUCCESS,
        stdout="Portfolio created at /workspace/portfolio.html",
        evidence="File portfolio.html verified (6,144 bytes).",
    ))

    executor = AgentExecutor()
    call_log = []

    def mock_call_tool(tool_name, params, speak=None):
        call_log.append(tool_name)
        if tool_name == "file_write":
            return "Portfolio created."
        if tool_name == "git_repo_mgr":
            return "✅ Git Push VERIFIED"
        return "Done."

    steps = [
        {"step": 1, "tool": "file_write",   "description": "Create portfolio",  "critical": True,  "parameters": {"path": "portfolio.html"}},
        {"step": 2, "tool": "git_repo_mgr", "description": "Push to GitHub",    "critical": False, "parameters": {"action": "push"}},
    ]

    step_results: dict = {}
    completed_steps: list = []

    with patch("brjarvis.agent.executor._call_tool", side_effect=mock_call_tool):
        result = executor._run_plan(
            steps=steps,
            step_results=step_results,
            completed_steps=completed_steps,
            goal="Create portfolio and push to GitHub",
            speak=None,
            cancel_flag=None,
            can_parallelize=False,
            task_id="retry_task",
            ledger=ledger,
        )

    # file_write (step_1) was already in the ledger as verified → should NOT be called again
    assert "file_write" not in call_log, (
        f"file_write was re-executed even though it was already verified in the ledger. "
        f"Calls: {call_log}"
    )
    # git_repo_mgr (step_2) was NOT in the ledger → should be executed
    assert "git_repo_mgr" in call_log, "git_repo_mgr (step_2) should have been executed."


@pytest.mark.unit
def test_unverified_step_is_not_skipped(tmp_path):
    """
    An UNVERIFIED step (only partial evidence) must be re-executed on retry,
    not silently skipped.
    """
    from brjarvis.agent.execution_ledger import ExecutionLedger, LedgerEntry, LedgerStatus
    from brjarvis.memory.canonical_db import CanonicalDatabaseManager
    from brjarvis.agent.executor import AgentExecutor

    db = CanonicalDatabaseManager(db_path=tmp_path / "test2.db")
    ledger = ExecutionLedger(db_manager=db)
    # Add an UNVERIFIED entry for step 1
    ledger.append(LedgerEntry(
        tool_name="file_write",
        task_id="rerun_task",
        step_id="step_1",
        status=LedgerStatus.SUCCESS,
        verification_status=LedgerStatus.UNVERIFIED,  # NOT verified
        stdout="Created something.",
    ))

    executor = AgentExecutor()
    call_log = []

    def mock_call_tool(tool_name, params, speak=None):
        call_log.append(tool_name)
        return "Done."

    steps = [
        {"step": 1, "tool": "file_write", "description": "Create file", "critical": True, "parameters": {}},
    ]

    with patch("brjarvis.agent.executor._call_tool", side_effect=mock_call_tool):
        executor._run_plan(
            steps=steps,
            step_results={},
            completed_steps=[],
            goal="Create file",
            speak=None,
            cancel_flag=None,
            can_parallelize=False,
            task_id="rerun_task",
            ledger=ledger,
        )

    # Unverified step must be re-executed
    assert "file_write" in call_log, "Unverified step should have been re-executed, not skipped."
