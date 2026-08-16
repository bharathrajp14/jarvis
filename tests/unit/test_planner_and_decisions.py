# tests/unit/test_planner_and_decisions.py — Planner & Decision Subsystem Unit Tests
"""
Unit tests validating:
1. Planner memory & experience ingestion
2. Plan cycle prevention and validation
3. Decision receipts recording and querying
4. Decision consistency validation against proposed actions
5. Execution ledger append-only semantics
"""
from __future__ import annotations

import time
import pytest
from brjarvis.agent.execution_ledger import ExecutionLedger, LedgerEntry, LedgerStatus
from brjarvis.agent.planner import _validate_and_sanitize_plan
from brjarvis.memory.canonical_db import CanonicalDatabaseManager
from brjarvis.reasoning.decision_engine import DecisionEngine


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_decisions.db"
    return CanonicalDatabaseManager(db_path=db_file)


@pytest.fixture
def decision_engine(temp_db):
    return DecisionEngine(db_manager=temp_db)


@pytest.fixture
def execution_ledger(temp_db):
    return ExecutionLedger(db_manager=temp_db)


def test_plan_sanitization_and_cycle_prevention():
    """Verify that invalid dependencies and cycles are sanitized."""
    raw_plan = {
        "goal": "Build REST API",
        "can_parallelize": True,
        "steps": [
            {
                "step": 1,
                "tool": "file_controller",
                "description": "Create app.py",
                "parameters": {"path": "app.py"},
                "depends_on": [1],  # self-dependency cycle -> should be filtered
                "parallel": False,
            },
            {
                "step": 2,
                "tool": "code_helper",
                "description": "Write FastAPI routes",
                "parameters": {"file": "app.py"},
                "depends_on": [1, 3],  # forward-dependency on future step 3 -> should be filtered
                "parallel": False,
            },
        ],
    }

    sanitized = _validate_and_sanitize_plan(raw_plan, "Build REST API")
    assert len(sanitized["steps"]) == 2
    assert sanitized["steps"][0]["depends_on"] == []  # self-dep removed
    assert sanitized["steps"][1]["depends_on"] == [1]  # forward-dep 3 removed, 1 kept


def test_decision_receipt_creation_and_query(decision_engine):
    """Verify structured decision recording and receipt extraction."""
    dec = decision_engine.record_decision(
        question="Which database to use for state persistence?",
        goal="Select reliable WAL storage",
        selected_option="SQLite WAL",
        rejected_options=["MongoDB", "Flat JSON"],
        task_id="task_arch_101",
        evidence="SQLite with WAL mode provides single-file local-first zero-latency transactions",
        constraints=["local-first", "atomic transactions"],
        risk_level="low",
        confidence=0.98,
        expected_outcome="Durable state without external daemon dependencies",
    )

    assert dec.decision_id is not None
    assert dec.selected_option == "SQLite WAL"
    assert "Flat JSON" in dec.rejected_options

    receipt = dec.to_receipt()
    assert receipt["decision_id"] == dec.decision_id
    assert receipt["selected_option"] == "SQLite WAL"
    assert receipt["confidence"] == 0.98

    # Query back from DB
    retrieved = decision_engine.get_decision(dec.decision_id)
    assert retrieved is not None
    assert retrieved.question == "Which database to use for state persistence?"


def test_decision_consistency_validation(decision_engine):
    """Verify that an action attempting a previously rejected alternative is flagged."""
    decision_engine.record_decision(
        question="How should we store application secrets?",
        goal="Secure token handling",
        selected_option="OS Keyring / Encrypted Vault",
        rejected_options=["Plaintext JSON file", "Plaintext memory notes"],
        evidence="Plaintext secrets leak into logs and git repositories",
    )

    # Valid action
    is_valid, reason = decision_engine.validate_action_against_decisions(
        "Store API token in OS Keyring securely"
    )
    assert is_valid is True
    assert reason is None

    # Conflicting action attempting rejected approach
    is_invalid, reason = decision_engine.validate_action_against_decisions(
        "Save API keys into Plaintext JSON file for easy debugging"
    )
    assert is_invalid is False
    assert "conflicts with Decision" in reason
    assert "Plaintext JSON file" in reason


def test_execution_ledger_append_and_verification(execution_ledger):
    """Verify append-only ledger entries and verification checks."""
    entry = LedgerEntry(
        task_id="task_build_1",
        step_id="step_1",
        tool_name="file_writer",
        status=LedgerStatus.SUCCESS,
        stdout="File created successfully: main.py",
        return_code=0,
        duration_seconds=0.12,
        evidence="File main.py exists on disk (142 bytes)",
        verification_status=LedgerStatus.SUCCESS,
    )
    entry_id = execution_ledger.append(entry)
    assert entry_id is not None

    entries = execution_ledger.get_task_entries("task_build_1")
    assert len(entries) == 1
    assert entries[0].tool_name == "file_writer"
    assert entries[0].status == LedgerStatus.SUCCESS

    # Step verification check
    assert execution_ledger.step_is_verified("task_build_1", "step_1") is True
    assert execution_ledger.step_is_verified("task_build_1", "step_2") is False

    report = execution_ledger.build_evidence_report("task_build_1")
    assert "Step step_1 [file_writer] ✅ SUCCESS" in report
