# tools/sandbox.py
"""
Code sandbox for JARVIS MK37 & MK38.
Executes code in an isolated subprocess jail with strict environment filtering and timeout protection.
Cross-platform: Windows, Linux, macOS.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from tools.sandbox_process import get_sandbox_runner, SandboxedProcessRunner

logger = logging.getLogger(__name__)


class CodeSandbox:
    """Subprocess code execution sandbox wrapper for backward compatibility."""

    ALLOWED_LANGS = {"python", "javascript", "bash", "powershell"}

    def __init__(self):
        self.runner = get_sandbox_runner()

    def run(self, code: str, lang: str = "python", timeout: int = 30) -> dict:
        """Run code inside the isolated sandbox process."""
        res = self.runner.execute(code=code, lang=lang, timeout=timeout)
        if not res.get("success", False) and "error" in res:
            return {"error": res["error"], "stdout": res.get("stdout", ""), "stderr": res.get("stderr", "")}
        return {
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "returncode": res.get("returncode", 0)
        }
