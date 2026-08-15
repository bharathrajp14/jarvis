# tools/sandbox.py — Code Sandbox Powered by UniversalExecutionRuntime
"""
Code sandbox for JARVIS MK37, MK38 & MK40.
Executes code in an isolated subprocess jail with strict environment filtering,
automatic dependency preflight, virtual environment resolution, and timeout protection.
Cross-platform: Windows, Linux, macOS.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.execution.types import ExecutionStatus
from core.execution.universal_runtime import get_universal_runtime
from tools.sandbox_process import get_sandbox_runner, SandboxedProcessRunner

logger = logging.getLogger(__name__)


class CodeSandbox:
    """Subprocess code execution sandbox wrapper powered by UniversalExecutionRuntime."""

    ALLOWED_LANGS = {"python", "javascript", "bash", "powershell"}

    def __init__(self):
        self.runtime = get_universal_runtime()
        self.runner = get_sandbox_runner()

    def run(self, code: str, lang: str = "python", timeout: int = 30) -> dict:
        """Run code inside the isolated sandbox process with verified execution."""
        try:
            exec_res = self.runtime.execute_code(
                code=code,
                lang=lang,
                timeout_sec=float(timeout),
                auto_repair=True,
            )
            return {
                "success": exec_res.success,
                "status": exec_res.status.value,
                "verified": exec_res.verified,
                "stdout": exec_res.stdout,
                "stderr": exec_res.stderr,
                "returncode": exec_res.return_code,
                "evidence": exec_res.evidence,
                "error": exec_res.error,
                "artifacts": exec_res.artifacts,
                "host_artifacts": exec_res.host_artifacts,
            }
        except Exception as exc:
            logger.error("CodeSandbox execution fallback: %s", exc)
            res = self.runner.execute(code=code, lang=lang, timeout=timeout)
            return {
                "success": res.get("success", False),
                "stdout": res.get("stdout", ""),
                "stderr": res.get("stderr", ""),
                "returncode": res.get("returncode", -1),
                "error": res.get("error"),
                "artifacts": res.get("artifacts", []),
                "host_artifacts": res.get("host_artifacts", []),
            }
