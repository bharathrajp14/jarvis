# tools/sandbox.py — Code Sandbox Powered by UniversalExecutionRuntime
"""
Code sandbox for JARVIS MK37, MK38 & MK40.
Executes code in an isolated subprocess jail with strict environment filtering,
automatic dependency preflight, virtual environment resolution, and timeout protection.
Cross-platform: Windows, Linux, macOS.
"""
from __future__ import annotations

import logging
import os

from brjarvis.core.execution.universal_runtime import get_universal_runtime

from .sandbox_process import get_sandbox_runner

logger = logging.getLogger(__name__)


class CodeSandbox:
    """Code-execution gateway that fails closed without a real isolation backend."""

    ALLOWED_LANGS = {"python", "javascript", "bash", "powershell"}

    def __init__(self):
        self.runtime = get_universal_runtime()
        self.runner = get_sandbox_runner()

    def run(self, code: str, lang: str = "python", timeout: int = 30) -> dict:
        """Run code inside the isolated sandbox process with verified execution."""
        unsafe_host_execution = os.environ.get("JARVIS_ENABLE_UNSAFE_HOST_EXECUTION", "false").strip().lower()
        if unsafe_host_execution not in {"1", "true", "yes", "on"}:
            return {
                "success": False,
                "status": "BLOCKED",
                "verified": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": (
                    "Code execution is disabled because no OS-isolated sandbox is configured. "
                    "Set JARVIS_ENABLE_UNSAFE_HOST_EXECUTION=true only in a disposable, trusted environment."
                ),
                "artifacts": [],
                "host_artifacts": [],
            }
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
            logger.error("CodeSandbox isolated runtime unavailable: %s", exc)
            return {
                "success": False,
                "status": "BLOCKED",
                "verified": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": "The isolated execution runtime failed; insecure host fallback was not used.",
                "artifacts": [],
                "host_artifacts": [],
            }
