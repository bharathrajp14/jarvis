# tests/integration/test_execution_integrity_master.py — Master Execution Integrity & Self-Repair Test Suite
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

from actions.open_app import open_app
from agent.stage_decomposer import StageCapability, StageDecomposer
from agent.task_state import TaskCriterion, TaskState, TaskStatus, get_task_state_manager
from core.execution.capability_checker import get_capability_checker
from core.execution.completion_gate import TaskCompletionGate, get_task_completion_gate
from core.execution.types import ApplicationStatus, ExecutionStatus
from core.execution.verifier import ApplicationVerifier, DocumentVerifier, FileVerifier, get_universal_verifier


class TestExecutionIntegrityMaster:
    """Master regression test suite for Universal Execution Integrity & Self-Repair."""

    def test_windows_launch_path_handling(self, tmp_path):
        """Test Windows launching with paths containing spaces and parentheses."""
        sample_file = tmp_path / "Audit Report (Q3 Final).txt"
        sample_file.write_text("Audit report findings and metrics.", encoding="utf-8")

        res = open_app(parameters={"app_name": str(sample_file)})
        assert isinstance(res, str)
        # Should not throw exception and should report status
        assert any(tag in res for tag in ("[OPEN_VERIFIED]", "[PROCESS_STARTED]", "[SUCCESS_UNVERIFIED]", "[SUCCESS_VERIFIED]", "launched", "sent"))

    def test_unverified_launch_produces_partial_success(self, tmp_path):
        """Force unverified launch and assert TaskCompletionGate assigns PARTIAL_SUCCESS, never SUCCESS_VERIFIED."""
        valid_doc = tmp_path / "valid_document.docx"
        valid_doc.write_text("Dummy docx content", encoding="utf-8")

        gate = get_task_completion_gate()
        steps = [
            {
                "step_id": 1,
                "tool": "create_word_document",
                "status": "SUCCESS_VERIFIED",
                "is_critical": True,
                "parameters": {"filename": str(valid_doc)},
                "result": "Created document.",
            },
            {
                "step_id": 2,
                "tool": "open_app",
                "status": "SUCCESS_UNVERIFIED",
                "is_critical": False,
                "parameters": {"app_name": str(valid_doc)},
                "result": f"[SUCCESS_UNVERIFIED] Launch command sent for '{valid_doc}'. No visible window detected.",
            }
        ]

        eval_res = gate.evaluate_task("Create and open document", steps)
        assert eval_res.is_approved is True
        assert eval_res.final_status == ExecutionStatus.PARTIAL_SUCCESS
        assert eval_res.final_status != ExecutionStatus.SUCCESS_VERIFIED
        assert len(eval_res.degraded_steps) > 0

    def test_task_context_isolation_no_cross_contamination(self):
        """Ensure Task A (Comparison) and Task B (Workspace Org) have zero context contamination."""
        decomposer = StageDecomposer()

        # Task A: OpenClaw vs BR JARVIS
        stages_a = decomposer.decompose("Compare OpenClaw and BR JARVIS architecture and features")
        doc_stage_a = next((s for s in stages_a if s.capability == StageCapability.DOC_CODE_GENERATION), None)
        assert doc_stage_a is not None
        assert "OpenClaw" in doc_stage_a.parameters.get("title", "")

        # Task B: Workspace Organization
        stages_b = decomposer.decompose("Perform workspace organization and catalog temporary files")
        doc_stage_b = next((s for s in stages_b if s.capability == StageCapability.DOC_CODE_GENERATION), None)
        assert doc_stage_b is not None
        assert "Workspace" in doc_stage_b.parameters.get("title", "")
        assert "OpenClaw" not in doc_stage_b.parameters.get("title", "")

    def test_layered_artifact_verification_vs_open_verification(self, tmp_path):
        """Validate that ARTIFACT_VERIFIED and OPEN_VERIFIED are discrete, layered checks."""
        report_file = tmp_path / "executive_summary.json"
        report_file.write_text('{"summary": "Verified system performance", "score": 98}', encoding="utf-8")

        # Layer 1: Physical File Verification
        f_res = FileVerifier.verify_file(report_file)
        assert f_res.verified is True
        assert f_res.status == ExecutionStatus.SUCCESS_VERIFIED

        # Layer 2: Structural Document Verification
        d_res = DocumentVerifier.verify_document(report_file)
        assert d_res.verified is True
        assert d_res.status == ExecutionStatus.SUCCESS_VERIFIED

        # Layer 3: Application / Window Verification (simulating nonexistent window)
        w_res = ApplicationVerifier.verify_window_open(window_title_keyword="nonexistent_fake_app_window_xyz")
        assert w_res.verified is False
        assert w_res.status == ExecutionStatus.SUCCESS_UNVERIFIED

    def test_corrupted_artifact_fails_completion_gate(self, tmp_path):
        """Ensure corrupted or 0-byte file causes TaskCompletionGate to reject completion."""
        corrupted_file = tmp_path / "corrupted_file.txt"
        # 0 bytes
        corrupted_file.touch()

        gate = get_task_completion_gate()
        steps = [
            {
                "step_id": 1,
                "tool": "file_write",
                "status": "SUCCESS_VERIFIED",
                "is_critical": True,
                "parameters": {"path": str(corrupted_file)},
                "result": "Wrote 0 bytes.",
            }
        ]

        eval_res = gate.evaluate_task("Write output", steps)
        assert eval_res.is_approved is False
        assert eval_res.final_status == ExecutionStatus.FAILED
        assert len(eval_res.blocking_reasons) > 0

    def test_task_state_criteria_breakdown(self):
        """Test TaskState with explicit criteria tracking (C1..Cn)."""
        criteria = [
            TaskCriterion(criterion_id="C1", description="PDF generated", status="VERIFIED", evidence="5325 bytes on disk"),
            TaskCriterion(criterion_id="C2", description="PDF readable", status="VERIFIED", evidence="Parsed 2 pages"),
            TaskCriterion(criterion_id="C3", description="Viewer window open", status="FAILED", evidence="No window detected"),
        ]

        state = TaskState(
            task_id="task_test_001",
            user_request="Create PDF and open it",
            goal="Create PDF and open it",
            status=TaskStatus.RUNNING,
            criteria=criteria,
        )

        state_dict = state.to_dict()
        assert len(state_dict["criteria"]) == 3
        assert state_dict["criteria"][0]["status"] == "VERIFIED"
        assert state_dict["criteria"][2]["status"] == "FAILED"

        # Deserialize
        restored = TaskState.from_dict(state_dict)
        assert restored.task_id == "task_test_001"
        assert len(restored.criteria) == 3
        assert restored.criteria[2].criterion_id == "C3"
