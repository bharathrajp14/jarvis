# tests/unit/test_contract_truth_levels.py — Canonical Truth Levels & Contract Invariant Validation
"""
BR JARVIS MK40.2 Truth Level & Contract Invariant Suite.
Enforces the 9-tier truth hierarchy:
1. CODE_EXISTS
2. IMPORTS
3. INITIALIZES
4. CALLS
5. EXECUTES
6. SIDE_EFFECT_OCCURRED
7. ARTIFACT_VALID
8. PHYSICAL_STATE_VERIFIED
9. TASK_VERIFIED

Invariants:
- A lower truth level NEVER implies a higher truth level.
- Tool returning True or exit code 0 does NOT imply physical side effect verified.
- File existence does NOT imply document structural validity.
- Document creation does NOT imply application launch or window active.
- API call dispatched does NOT imply submission verified.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest

from brjarvis.core.execution.types import ExecutionStatus, VerificationOutcome
from brjarvis.core.execution.verifier import (
    FileVerifier,
    DocumentVerifier,
    ApplicationVerifier,
    OutputContractValidator,
    UniversalVerifier,
    get_universal_verifier,
)
from brjarvis.core.execution.completion_gate import TaskCompletionGate, get_task_completion_gate
from brjarvis.tools.tool_runtime import ToolResult, ToolExecutionStatus


class TestTruthLevelHierarchy:
    """Test explicit truth level isolation and non-implication invariants."""

    def test_level_5_executes_does_not_imply_level_6_side_effect_verified(self):
        """A tool returning success text does not prove side effects occurred."""
        # Simulated unverified tool result (command returned 0 but output contains fatal traceback)
        output_with_traceback = "Process exited with code 0.\nTraceback (most recent call last):\n  File 'worker.py', line 10\nZeroDivisionError: division by zero"
        validator_res = OutputContractValidator.validate_output(output_with_traceback, return_code=0)
        assert validator_res.verified is False
        assert validator_res.status == ExecutionStatus.FAILED

    def test_level_6_file_exists_does_not_imply_level_7_artifact_valid(self, tmp_path):
        """A file existing on disk does not imply it is structurally valid or non-empty."""
        # 1. Zero-byte file
        empty_doc = tmp_path / "corrupt.docx"
        empty_doc.write_bytes(b"")
        v_res = FileVerifier.verify_file(empty_doc)
        assert v_res.verified is False
        assert v_res.error == "FILE_EMPTY"

        # 2. Corrupt document (random garbage bytes with .docx extension)
        corrupt_doc = tmp_path / "garbage.docx"
        corrupt_doc.write_bytes(b"NOT_A_VALID_ZIP_OR_DOCX_FILE_HEADER_XYZ")
        doc_res = DocumentVerifier.verify_document(corrupt_doc)
        assert doc_res.verified is False
        assert doc_res.status == ExecutionStatus.VERIFICATION_FAILED
        assert doc_res.error in ("PARSE_ERROR", "INVALID_ZIP_ARCHIVE", "DOC_PARSE_ERROR", "INVALID_DOCX")

    def test_level_7_artifact_valid_does_not_imply_level_8_open_verified(self, tmp_path):
        """A valid document existing on disk does not imply it was opened in a viewer window."""
        valid_json = tmp_path / "valid.json"
        valid_json.write_text('{"report": "ready", "items": [1, 2, 3]}', encoding="utf-8")
        
        # Verify artifact is valid on disk (Level 7)
        doc_res = DocumentVerifier.verify_document(valid_json)
        assert doc_res.verified is True
        assert doc_res.status == ExecutionStatus.SUCCESS_VERIFIED

        # Verify application open verification requires active window handle (Level 8)
        app_res = UniversalVerifier.verify_window(app_name="NonexistentViewerWindowXYZ")
        assert app_res.verified is False
        assert app_res.status == ExecutionStatus.SUCCESS_UNVERIFIED

    def test_level_8_app_command_sent_does_not_imply_level_9_task_verified(self):
        """An unverified application launch must not approve a task as SUCCESS_VERIFIED."""
        gate = get_task_completion_gate()
        steps = [
            {
                "step_id": 1,
                "tool": "open_app",
                "status": "SUCCESS_UNVERIFIED",
                "is_critical": False,
                "parameters": {"app_name": "Chrome"},
                "result": "Launch command dispatched.",
            }
        ]
        eval_res = gate.evaluate_task("Open Chrome Browser", steps)
        assert eval_res.is_approved is True
        # Must be classified as PARTIAL_SUCCESS, NOT SUCCESS_VERIFIED
        assert eval_res.final_status == ExecutionStatus.PARTIAL_SUCCESS
        assert "Unverified Items" in eval_res.evidence_summary

    def test_level_9_task_completion_gate_strictly_enforces_critical_step_success(self, tmp_path):
        """A task with even one critical step failure MUST be rejected by the completion gate."""
        gate = get_task_completion_gate()
        valid_file = tmp_path / "output.txt"
        valid_file.write_text("Analysis complete", encoding="utf-8")

        steps = [
            {
                "step_id": 1,
                "tool": "file_write",
                "status": "SUCCESS_VERIFIED",
                "is_critical": True,
                "parameters": {"path": str(valid_file)},
                "result": "File created.",
            },
            {
                "step_id": 2,
                "tool": "database_sync",
                "status": "FAILED",
                "is_critical": True,
                "error": "Connection timeout to DB",
            }
        ]
        eval_res = gate.evaluate_task("Write and Sync Report", steps)
        assert eval_res.is_approved is False
        assert eval_res.final_status == ExecutionStatus.FAILED
        assert any("Critical Step 2" in reason for reason in eval_res.blocking_reasons)


class TestToolResultContract:
    """Test ToolResult contract standardization."""

    def test_tool_result_canonical_fields(self):
        res = ToolResult(
            tool_name="web_search",
            task_id="task_100",
            step_id="step_1",
            status=ToolExecutionStatus.SUCCESS,
            data={"results": ["https://example.com"]},
            evidence="Found 1 result via DuckDuckGo",
            execution_ms=150.0,
            verified=True,
        )

        assert res.tool == "web_search"
        assert res.task_id == "task_100"
        assert res.step_id == "step_1"
        assert res.success is True
        assert res.duration == 0.15
        assert res.verification is True
        
        d = res.to_dict()
        assert d["task_id"] == "task_100"
        assert d["step_id"] == "step_1"
        assert d["status"] == "SUCCESS"
        assert d["verified"] is True
        assert d["duration_ms"] == 150.0

    def test_tool_result_failure_statuses(self):
        statuses = [
            ToolExecutionStatus.FAILED,
            ToolExecutionStatus.TIMEOUT,
            ToolExecutionStatus.BLOCKED,
            ToolExecutionStatus.NOT_AVAILABLE,
            ToolExecutionStatus.REQUIRES_APPROVAL,
        ]
        for st in statuses:
            r = ToolResult(tool_name="test_tool", status=st, message=f"Reason for {st.value}")
            assert r.success is False
            assert r.status == st
            assert r.to_dict()["status"] == st.value
