# tests/unit/test_sandboxed_process.py — Unit Tests for Sandboxed Process Runner
from __future__ import annotations

import os
import pytest
from tools.sandbox_process import SandboxedProcessRunner
from tools.sandbox import CodeSandbox


def test_sandbox_process_basic_execution():
    runner = SandboxedProcessRunner()
    result = runner.execute("print(40 + 2)", lang="python")
    assert result["success"] is True
    assert result["stdout"].strip() == "42"
    assert result["returncode"] == 0


def test_sandbox_process_strips_secret_env_vars():
    os.environ["SUPER_SECRET_API_KEY"] = "sk-leaked-secret-value-12345"
    runner = SandboxedProcessRunner()
    code = "import os; print('SECRET_FOUND=' + str('SUPER_SECRET_API_KEY' in os.environ))"
    result = runner.execute(code, lang="python")
    assert result["success"] is True
    assert "SECRET_FOUND=False" in result["stdout"]


def test_sandbox_process_timeout_enforcement():
    runner = SandboxedProcessRunner()
    code = "import time; time.sleep(10)"
    result = runner.execute(code, lang="python", timeout=1)
    assert result["success"] is False
    assert result.get("timed_out", False) is True or "timed out" in result.get("error", "").lower()


def test_code_sandbox_wrapper():
    sandbox = CodeSandbox()
    res = sandbox.run("x = 10; y = 20; print(f'SUM={x+y}')")
    assert "SUM=30" in res["stdout"]
