"""
Test 32 — Portfolio Creation & GitHub Push — E2E Regression Test
MK40.2 §39 (full workflow validation)

Verifies that:
  - Creating a portfolio produces a real file artifact (not just a success string)
  - Git operations are tracked with returncode evidence
  - The final gate status is SUCCESS_VERIFIED (or PARTIAL_SUCCESS if push skipped)
  - The final response is derived from ledger evidence — never a fabricated sentence
  - The task's user_request is preserved verbatim in TaskState

This test runs in two modes:
  - CI mode: mocks git push and file creation; tests the evidence flow
  - Full mode: runs against real workspace if JARVIS_E2E_REAL=1 is set
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

GOAL = (
    "Create a professional portfolio using my available information, "
    "save it in the canonical workspace, validate it, initialize/update Git, "
    "push it to my GitHub repository, verify the remote repository, "
    "open the resulting portfolio in the correct application, "
    "verify that it is actually open, and report exactly what happened."
)

REAL_MODE = os.environ.get("JARVIS_E2E_REAL", "0") == "1"


# ── Helper factories ──────────────────────────────────────────────────────────


def _make_ledger_with_portfolio_and_push(tmp_path, push_success: bool = True):
    """Create a ledger with a complete portfolio + push workflow."""
    from brjarvis.agent.execution_ledger import ExecutionLedger, LedgerEntry, LedgerStatus
    from brjarvis.memory.canonical_db import CanonicalDatabaseManager

    db = CanonicalDatabaseManager(db_path=tmp_path / "e2e.db")
    ledger = ExecutionLedger(db_manager=db)

    ledger.append(
        LedgerEntry(
            tool_name="file_write",
            task_id="e2e_task",
            step_id="step_1",
            status=LedgerStatus.SUCCESS,
            verification_status=LedgerStatus.SUCCESS,
            stdout="portfolio/index.html created (8,192 bytes)",
            evidence="File 'portfolio/index.html' verified on disk (8,192 bytes).",
            side_effects=["file:created:/workspace/portfolio/index.html"],
        )
    )
    ledger.append(
        LedgerEntry(
            tool_name="git_repo_mgr",
            task_id="e2e_task",
            step_id="step_2",
            status=LedgerStatus.SUCCESS,
            verification_status=LedgerStatus.SUCCESS,
            stdout="Staged all. Committed: hash=abc123def456",
            evidence="Git commit created (hash: abc123def456).",
        )
    )
    if push_success:
        ledger.append(
            LedgerEntry(
                tool_name="git_repo_mgr",
                task_id="e2e_task",
                step_id="step_3",
                status=LedgerStatus.SUCCESS,
                verification_status=LedgerStatus.SUCCESS,
                stdout="✅ Git Push VERIFIED (remote branch updated)",
                evidence="push returncode=0, remote_hash=abc123def456, remote_verified=True",
            )
        )
    else:
        ledger.append(
            LedgerEntry(
                tool_name="git_repo_mgr",
                task_id="e2e_task",
                step_id="step_3",
                status=LedgerStatus.FAILED,
                verification_status=LedgerStatus.FAILED,
                stdout="❌ Git Push FAILED",
                evidence="push returncode=128, auth failure",
                error="Authentication failed for GitHub",
            )
        )
    return ledger


# ── Test 32: CI mode ─────────────────────────────────────────────────────────


@pytest.mark.e2e
def test_portfolio_github_push_success_verified(tmp_path):
    """
    MK40.2 Test 32 (CI): Full portfolio + push workflow.
    Gate must return SUCCESS_VERIFIED when all steps complete with evidence.
    Final response must NOT be a fabricated Gemini summary.
    """
    from brjarvis.core.execution.completion_gate import TaskCompletionGate

    ledger = _make_ledger_with_portfolio_and_push(tmp_path, push_success=True)
    entries = ledger.get_task_entries("e2e_task")

    gate = TaskCompletionGate(
        verifier=MagicMock(
            validate_output=MagicMock(return_value=MagicMock(verified=True, error=None, details="Clean")),
            verify_file=MagicMock(return_value=MagicMock(verified=True)),
            verify_window=MagicMock(return_value=MagicMock(verified=False)),
        )
    )

    completed_steps = [
        {
            "step": 1,
            "tool": "file_write",
            "status": "SUCCESS",
            "critical": True,
            "parameters": {},
            "result": "portfolio created",
        },
        {
            "step": 2,
            "tool": "git_repo_mgr",
            "status": "SUCCESS",
            "critical": True,
            "parameters": {},
            "result": "committed",
        },
        {
            "step": 3,
            "tool": "git_repo_mgr",
            "status": "SUCCESS",
            "critical": True,
            "parameters": {},
            "result": "pushed",
        },
    ]

    result = gate.evaluate_task(
        goal=GOAL,
        steps=completed_steps,
        ledger_entries=entries,
        required_operations=["CREATE_PORTFOLIO", "PUSH_TO_GITHUB"],
    )

    # All required operations must be covered
    missing = result.required_operations_missing
    assert not missing, f"Required operations not covered: {missing}"
    # Status must be SUCCESS_VERIFIED or at worst PARTIAL_SUCCESS (if window not opened)
    assert result.final_status.value in ("SUCCESS_VERIFIED", "PARTIAL_SUCCESS"), (
        f"Expected SUCCESS_VERIFIED or PARTIAL_SUCCESS, got {result.final_status.value}. "
        f"Reasons: {result.blocking_reasons}"
    )


@pytest.mark.e2e
def test_portfolio_partial_success_when_push_fails(tmp_path):
    """
    MK40.2 Test 32 (CI): Portfolio created but push failed.
    Gate must NOT report SUCCESS_VERIFIED. It must reflect PARTIAL or FAILED.
    """
    from brjarvis.core.execution.completion_gate import TaskCompletionGate

    ledger = _make_ledger_with_portfolio_and_push(tmp_path, push_success=False)
    entries = ledger.get_task_entries("e2e_task")

    gate = TaskCompletionGate(
        verifier=MagicMock(
            validate_output=MagicMock(return_value=MagicMock(verified=True, error=None, details="Clean")),
            verify_file=MagicMock(return_value=MagicMock(verified=True)),
            verify_window=MagicMock(return_value=MagicMock(verified=False)),
        )
    )

    steps = [
        {
            "step": 1,
            "tool": "file_write",
            "status": "SUCCESS",
            "critical": True,
            "parameters": {},
            "result": "portfolio created",
        },
        {
            "step": 2,
            "tool": "git_repo_mgr",
            "status": "SUCCESS",
            "critical": True,
            "parameters": {},
            "result": "committed",
        },
        {
            "step": 3,
            "tool": "git_repo_mgr",
            "status": "FAILED",
            "critical": True,
            "parameters": {},
            "error": "auth failure",
        },
    ]

    result = gate.evaluate_task(
        goal="Create portfolio and push to GitHub",
        steps=steps,
        ledger_entries=entries,
        required_operations=["CREATE_PORTFOLIO", "PUSH_TO_GITHUB"],
    )

    assert result.final_status.value != "SUCCESS_VERIFIED", (
        f"Push failed but gate returned SUCCESS_VERIFIED. Evidence: {result.evidence_summary}"
    )


@pytest.mark.e2e
def test_task_user_request_preserved_in_state(tmp_path):
    """
    MK40.2 §1: user_request must be stored verbatim and never mutated.
    Verify this via TaskStateManager.create_task().
    """
    from brjarvis.agent.task_state import TaskStateManager
    from brjarvis.memory.canonical_db import CanonicalDatabaseManager

    db = CanonicalDatabaseManager(db_path=tmp_path / "state.db")
    mgr = TaskStateManager(db_manager=db)

    original_goal = GOAL
    state = mgr.create_task(
        goal=original_goal,
        goal_spec={
            "required_operations": ["CREATE_PORTFOLIO", "PUSH_TO_GITHUB"],
            "acceptance_criteria": [],
        },
    )

    retrieved = mgr.get_task(state.task_id)
    assert retrieved is not None
    assert retrieved.user_request == original_goal, (
        f"user_request was modified! Original: '{original_goal[:60]}...', Retrieved: '{retrieved.user_request[:60]}...'"
    )
    assert retrieved.required_operations == ["CREATE_PORTFOLIO", "PUSH_TO_GITHUB"]


@pytest.mark.e2e
@pytest.mark.skipif(not REAL_MODE, reason="Real E2E test skipped in CI (set JARVIS_E2E_REAL=1 to enable)")
def test_portfolio_full_real_workflow():
    """
    MK40.2 Test 39 (real): Full end-to-end with actual workspace, git, and GitHub.
    Only runs when JARVIS_E2E_REAL=1 is set.
    """
    from brjarvis.agent.executor import AgentExecutor

    executor = AgentExecutor()
    summary = executor.execute(goal=GOAL)

    # The summary must NOT be a fabricated Gemini sentence
    fabrication_indicators = [
        "I have successfully completed",
        "I have created and pushed",
        "everything was successful",
    ]
    for indicator in fabrication_indicators:
        assert indicator.lower() not in summary.lower(), (
            f"Response contains fabricated success language: '{indicator}'. Full response: {summary[:300]}"
        )

    # Must contain evidence markers
    evidence_markers = ["verified", "returncode", "steps", "evidence"]
    has_evidence = any(m in summary.lower() for m in evidence_markers)
    assert has_evidence, (
        f"Response does not contain any evidence markers ({evidence_markers}). Full response: {summary[:300]}"
    )
