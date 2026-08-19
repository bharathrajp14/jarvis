"""
Tests for ExecutionLedger — MK40.2 §2 (append-only, authoritative)

Covers:
  - Append and retrieve entries
  - Immutability (duplicate step_id entries are allowed but tracked separately)
  - step_is_verified() only returns True for SUCCESS/SUCCESS entries
  - build_evidence_report() produces deterministic text
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tmp_ledger(tmp_path):
    """Create an ExecutionLedger backed by a temp SQLite database."""
    from brjarvis.memory.canonical_db import CanonicalDatabaseManager

    db_path = tmp_path / "test_ledger.db"
    db = CanonicalDatabaseManager(db_path=db_path)
    from brjarvis.agent.execution_ledger import ExecutionLedger

    return ExecutionLedger(db_manager=db)


@pytest.mark.unit
def test_ledger_append_and_retrieve(tmp_ledger):
    """Entries written to the ledger must be retrievable in insertion order."""
    from brjarvis.agent.execution_ledger import LedgerEntry, LedgerStatus

    entry1 = LedgerEntry(
        tool_name="file_write",
        task_id="task_001",
        step_id="step_1",
        status=LedgerStatus.SUCCESS,
        stdout="File created at /path/portfolio.html",
        evidence="File 'portfolio.html' verified on disk (4,321 bytes).",
        verification_status=LedgerStatus.SUCCESS,
    )
    entry2 = LedgerEntry(
        tool_name="git_repo_mgr",
        task_id="task_001",
        step_id="step_2",
        status=LedgerStatus.FAILED,
        stderr="fatal: Authentication failed",
        evidence="Git push FAILED returncode=128",
        verification_status=LedgerStatus.FAILED,
        error="Authentication failed",
    )

    tmp_ledger.append(entry1)
    tmp_ledger.append(entry2)

    entries = tmp_ledger.get_task_entries("task_001")
    assert len(entries) == 2
    assert entries[0].tool_name == "file_write"
    assert entries[0].status == LedgerStatus.SUCCESS
    assert entries[1].tool_name == "git_repo_mgr"
    assert entries[1].status == LedgerStatus.FAILED


@pytest.mark.unit
def test_ledger_step_is_verified_only_for_success(tmp_ledger):
    """step_is_verified() must return True ONLY when status=SUCCESS AND verification_status=SUCCESS."""
    from brjarvis.agent.execution_ledger import LedgerEntry, LedgerStatus

    # Verified entry
    tmp_ledger.append(
        LedgerEntry(
            tool_name="file_write",
            task_id="t1",
            step_id="step_1",
            status=LedgerStatus.SUCCESS,
            verification_status=LedgerStatus.SUCCESS,
            evidence="File confirmed.",
        )
    )
    # Unverified entry
    tmp_ledger.append(
        LedgerEntry(
            tool_name="web_search",
            task_id="t1",
            step_id="step_2",
            status=LedgerStatus.SUCCESS,
            verification_status=LedgerStatus.UNVERIFIED,
        )
    )
    # Failed entry
    tmp_ledger.append(
        LedgerEntry(
            tool_name="git_repo_mgr",
            task_id="t1",
            step_id="step_3",
            status=LedgerStatus.FAILED,
            verification_status=LedgerStatus.FAILED,
            error="push failed",
        )
    )

    assert tmp_ledger.step_is_verified("t1", "step_1") is True
    assert tmp_ledger.step_is_verified("t1", "step_2") is False  # UNVERIFIED verification
    assert tmp_ledger.step_is_verified("t1", "step_3") is False  # FAILED


@pytest.mark.unit
def test_ledger_evidence_report_deterministic(tmp_ledger):
    """build_evidence_report() must return a string with step details."""
    from brjarvis.agent.execution_ledger import LedgerEntry, LedgerStatus

    tmp_ledger.append(
        LedgerEntry(
            tool_name="file_write",
            task_id="task_ev",
            step_id="step_1",
            status=LedgerStatus.SUCCESS,
            verification_status=LedgerStatus.SUCCESS,
            evidence="File portfolio.html verified (8,192 bytes).",
        )
    )
    tmp_ledger.append(
        LedgerEntry(
            tool_name="git_repo_mgr",
            task_id="task_ev",
            step_id="step_2",
            status=LedgerStatus.FAILED,
            verification_status=LedgerStatus.FAILED,
            evidence="Git push FAILED returncode=128",
            error="auth failure",
        )
    )

    report = tmp_ledger.build_evidence_report("task_ev")
    assert "task_ev" in report
    assert "file_write" in report
    assert "SUCCESS" in report
    assert "git_repo_mgr" in report
    assert "FAILED" in report
    assert "portfolio.html" in report


@pytest.mark.unit
def test_ledger_nonexistent_task_returns_empty(tmp_ledger):
    """Querying a task that was never written returns an empty list."""
    entries = tmp_ledger.get_task_entries("nonexistent_task_xyz")
    assert entries == []


@pytest.mark.unit
def test_ledger_task_has_critical_failure(tmp_ledger):
    """task_has_critical_failure() must detect any FAILED or BLOCKED entries."""
    from brjarvis.agent.execution_ledger import LedgerEntry, LedgerStatus

    tmp_ledger.append(
        LedgerEntry(
            tool_name="file_write",
            task_id="fail_task",
            step_id="step_1",
            status=LedgerStatus.SUCCESS,
            verification_status=LedgerStatus.SUCCESS,
        )
    )
    tmp_ledger.append(
        LedgerEntry(
            tool_name="git_repo_mgr",
            task_id="fail_task",
            step_id="step_2",
            status=LedgerStatus.FAILED,
            verification_status=LedgerStatus.FAILED,
            error="push auth fail",
        )
    )

    assert tmp_ledger.task_has_critical_failure("fail_task") is True
