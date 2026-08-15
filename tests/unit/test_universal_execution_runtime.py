# tests/unit/test_universal_execution_runtime.py — Comprehensive Unit Test Suite for Universal Execution Runtime
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

from core.execution.capability_checker import CapabilityChecker, get_capability_checker
from core.execution.completion_gate import TaskCompletionGate, get_task_completion_gate
from core.execution.dependency_resolver import DependencyResolver, get_dependency_resolver
from core.execution.environment_resolver import EnvironmentResolver, get_environment_resolver
from core.execution.process_runner import ProcessRunner, get_process_runner
from core.execution.recovery_manager import RecoveryManager, get_recovery_manager
from core.execution.trace import ExecutionTrace
from core.execution.types import (
    DependencyDeclaration,
    EnvironmentProfile,
    ExecutionResult,
    ExecutionStatus,
    RepairPolicy,
    RuntimeType,
)
from core.execution.universal_runtime import (
    UniversalExecutionRuntime,
    get_universal_runtime,
)
from core.execution.verifier import (
    ApplicationVerifier,
    BrowserVerifier,
    DirectoryVerifier,
    DocumentVerifier,
    FileVerifier,
    OutputContractValidator,
    UniversalVerifier,
    get_universal_verifier,
)


class TestEnvironmentResolver:
    """Test 6-tier deterministic environment resolution."""

    def test_python_virtualenv_resolution(self):
        resolver = get_environment_resolver()
        prof = resolver.resolve_python()
        assert prof.runtime_type == RuntimeType.PYTHON
        assert prof.executable != ""
        assert Path(prof.executable).exists()
        # In our workspace, project .venv must be resolved at Tier 2
        if (Path(resolver.default_project_root) / ".venv").exists():
            assert prof.precedence_tier == 2
            assert prof.is_virtualenv is True
            assert ".venv" in prof.executable.lower()

    def test_explicit_python_precedence(self):
        resolver = get_environment_resolver()
        explicit_py = sys.executable
        prof = resolver.resolve_python(explicit_path=explicit_py)
        assert prof.precedence_tier == 1
        assert prof.precedence_source == "explicit_configuration"
        assert prof.executable == str(Path(explicit_py).resolve())

    def test_system_executables_resolution(self):
        resolver = get_environment_resolver()
        git_prof = resolver.resolve_git()
        pwsh_prof = resolver.resolve_powershell()
        assert git_prof.runtime_type == RuntimeType.GIT
        assert pwsh_prof.runtime_type == RuntimeType.POWERSHELL


class TestDependencyResolver:
    """Test machine-readable dependency detection and import intelligence."""

    def test_module_to_package_mapping(self):
        dep = get_dependency_resolver()
        assert dep.map_module_to_package("fitz").lower() == "pymupdf"
        assert dep.map_module_to_package("docx").lower() == "python-docx"
        assert dep.map_module_to_package("cv2").lower() == "opencv-python"
        assert dep.map_module_to_package("PIL").lower() == "pillow"
        assert dep.map_module_to_package("sklearn").lower() == "scikit-learn"
        assert dep.map_module_to_package("yaml").lower() == "pyyaml"
        assert dep.map_module_to_package("bs4").lower() == "beautifulsoup4"
        assert dep.map_module_to_package("dotenv").lower() == "python-dotenv"
        assert dep.map_module_to_package("fpdf").lower() == "fpdf2"

    def test_extract_python_imports(self):
        dep = get_dependency_resolver()
        code = """
import os
import sys
import fitz
from docx import Document
from openpyxl.styles import Font
import unknown_custom_lib
"""
        imports = dep.extract_python_imports(code)
        assert "fitz" in imports
        assert "docx" in imports
        assert "openpyxl" in imports
        assert "unknown_custom_lib" in imports
        # Stdlib should be filtered out
        assert "os" not in imports
        assert "sys" not in imports

    def test_target_environment_import_verification(self):
        dep = get_dependency_resolver()
        env = get_environment_resolver().resolve_python()
        
        # Test standard installed package
        is_ok, ver = dep.verify_python_import("json", env)
        assert is_ok is True
        
        # Test nonexistent package
        is_ok, err = dep.verify_python_import("nonexistent_fake_package_xyz123", env)
        assert is_ok is False


class TestUniversalVerifier:
    """Test real-world physical side-effect verifiers."""

    def test_file_verifier(self, tmp_path):
        test_file = tmp_path / "sample.txt"
        test_file.write_text("Hello BR JARVIS", encoding="utf-8")

        res_ok = FileVerifier.verify_file(test_file)
        assert res_ok.verified is True
        assert res_ok.status == ExecutionStatus.SUCCESS_VERIFIED

        # Nonexistent file
        res_fail = FileVerifier.verify_file(tmp_path / "missing.txt")
        assert res_fail.verified is False
        assert res_fail.error == "FILE_NOT_FOUND"

        # Empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        res_empty = FileVerifier.verify_file(empty_file)
        assert res_empty.verified is False
        assert res_empty.error == "FILE_EMPTY"

    def test_document_verifier_json_and_csv(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text('{"status": "ok", "items": [1, 2, 3]}', encoding="utf-8")
        res_json = DocumentVerifier.verify_document(json_file)
        assert res_json.verified is True

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")
        res_csv = DocumentVerifier.verify_document(csv_file)
        assert res_csv.verified is True

    def test_browser_verifier_sandbox_leak_prevention(self):
        res_leak = BrowserVerifier.verify_browser_artifact("C:/tmp/jarvis_sandbox_jails/jail_123/report.html")
        assert res_leak.verified is False
        assert res_leak.status == ExecutionStatus.BLOCKED
        assert res_leak.error == "SANDBOX_PATH_EXPOSURE"

    def test_output_contract_validator_catches_hidden_errors(self):
        # Exit code 0 with traceback in output
        traceback_output = "Starting script...\nTraceback (most recent call last):\n  File 'main.py', line 2\nZeroDivisionError: division by zero"
        res = OutputContractValidator.validate_output(traceback_output, return_code=0)
        assert res.verified is False
        assert res.error in ("UNCAUGHT_PYTHON_EXCEPTION", "RUNTIME_MATH_ERROR")

        # Output with ModuleNotFoundError
        mod_output = "Traceback (most recent call last):\nModuleNotFoundError: No module named 'pypdf'"
        res_mod = OutputContractValidator.validate_output(mod_output, return_code=0)
        assert res_mod.verified is False
        assert res_mod.status == ExecutionStatus.MISSING_DEPENDENCY


class TestTaskCompletionGate:
    """Test centralized gate preventing false-success claims."""

    def test_rejects_task_with_critical_step_failure(self):
        gate = get_task_completion_gate()
        steps = [
            {"step_id": 1, "tool": "web_search", "status": "SUCCESS_VERIFIED", "is_critical": True, "result": "Search results found."},
            {"step_id": 2, "tool": "file_write", "status": "FAILED", "is_critical": True, "error": "Permission denied"},
        ]
        eval_res = gate.evaluate_task("Create Report", steps)
        assert eval_res.is_approved is False
        assert eval_res.final_status == ExecutionStatus.FAILED
        assert len(eval_res.blocking_reasons) > 0

    def test_rejects_task_with_missing_expected_artifact(self, tmp_path):
        gate = get_task_completion_gate()
        steps = [
            {
                "step_id": 1,
                "tool": "document_creator",
                "status": "SUCCESS_VERIFIED",
                "is_critical": True,
                "parameters": {"filename": str(tmp_path / "nonexistent_report.docx")},
                "result": "Created document.",
            }
        ]
        eval_res = gate.evaluate_task("Generate Executive Report", steps)
        assert eval_res.is_approved is False
        assert eval_res.final_status == ExecutionStatus.FAILED

    def test_approves_task_with_verified_artifacts(self, tmp_path):
        real_file = tmp_path / "verified_report.txt"
        real_file.write_text("Executive Analysis Findings", encoding="utf-8")

        gate = get_task_completion_gate()
        steps = [
            {
                "step_id": 1,
                "tool": "file_write",
                "status": "SUCCESS_VERIFIED",
                "is_critical": True,
                "parameters": {"path": str(real_file)},
                "result": f"Wrote to {real_file}",
            }
        ]
        eval_res = gate.evaluate_task("Write report", steps)
        assert eval_res.is_approved is True
        assert eval_res.final_status == ExecutionStatus.SUCCESS_VERIFIED
        assert len(eval_res.verified_artifacts) == 1


class TestUniversalExecutionRuntime:
    """Test master execution runtime."""

    def test_execute_python_code_with_venv(self):
        rt = get_universal_runtime()
        code = """
import sys
import math
print(f"PI={math.pi}")
"""
        res = rt.execute_code(code=code, lang="python", timeout_sec=10.0)
        assert res.success is True
        assert "PI=3.14" in res.stdout

    def test_execute_code_captures_error(self):
        rt = get_universal_runtime()
        code = "raise ValueError('Intentional test error')"
        res = rt.execute_code(code=code, lang="python", timeout_sec=10.0)
        assert res.success is False
        assert "ValueError" in res.stderr
