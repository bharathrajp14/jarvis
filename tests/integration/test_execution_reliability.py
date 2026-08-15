# tests/integration/test_execution_reliability.py — Integration Test Suite for End-to-End Reliability
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from core.execution.capability_checker import get_capability_checker
from core.execution.completion_gate import get_task_completion_gate
from core.execution.dependency_resolver import get_dependency_resolver
from core.execution.environment_resolver import get_environment_resolver
from core.execution.types import ExecutionStatus
from core.execution.universal_runtime import get_universal_runtime
from tools.sandbox import CodeSandbox


class TestExecutionReliabilityIntegration:
    """Integration test suite validating end-to-end execution reliability."""

    def test_run_code_with_complex_installed_libraries(self):
        sandbox = CodeSandbox()
        # Test code importing libraries installed in project .venv
        code = """
import pypdf
import docx
import openpyxl
import json

data = {"status": "ok", "libraries": ["pypdf", "docx", "openpyxl"]}
print(json.dumps(data))
"""
        res = sandbox.run(code=code, lang="python", timeout=15)
        assert res.get("success") is True or res.get("returncode") == 0
        parsed = json.loads(res.get("stdout", "{}"))
        assert parsed.get("status") == "ok"
        assert len(parsed.get("libraries", [])) == 3

    def test_capability_preflight_for_document_generation(self):
        cap = get_capability_checker()
        docx_cap = cap.check_document_generation(fmt="docx")
        pdf_cap = cap.check_document_generation(fmt="pdf")
        
        assert docx_cap.is_available is True
        assert pdf_cap.is_available is True

    def test_universal_runtime_diagnostics(self):
        rt = get_universal_runtime()
        diag = rt.diagnose_runtime()
        
        assert "environments" in diag
        assert "python" in diag["environments"]
        assert diag["environments"]["python"]["is_healthy"] is True
        assert "packages_in_python_venv" in diag
        assert len(diag["packages_in_python_venv"]) >= 5

    def test_execution_trace_records_full_lifecycle(self):
        rt = get_universal_runtime()
        trace = rt.start_trace("Inspect environment and verify execution")
        
        res = rt.execute_code(
            code="print('Execution trace validation')",
            lang="python",
            trace=trace,
            timeout_sec=10.0,
        )
        trace.complete(res.status, summary="Completed successfully")
        
        timeline = trace.format_timeline()
        assert "REQUEST" in timeline
        assert "ENVIRONMENT" in timeline
        assert "EXECUTION" in timeline
        assert "VALIDATION" in timeline
        assert "FINAL_STATUS" in timeline
        assert res.success is True
