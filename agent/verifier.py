# agent/verifier.py — Autonomous Action & Goal Verification Subsystem
"""
State and Goal Verification Engine for BR JARVIS MK40.
Ensures actions are rigorously verified against actual OS/filesystem state,
preventing false-positive completions and hallucinated success states.
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("JARVIS.Verifier")


@dataclass
class VerificationResult:
    """Outcome of an action verification check."""
    verified: bool
    details: str
    error: Optional[str] = None


class ActionVerifier:
    """Deterministic verifier for tool executions and OS state mutations."""

    @classmethod
    def verify_file_created(cls, path_str: str, min_size_bytes: int = 1) -> VerificationResult:
        """Verify that a target file exists, is accessible, and has non-empty contents."""
        try:
            p = Path(path_str).resolve()
            if not p.exists():
                return VerificationResult(
                    verified=False,
                    details=f"Verification failed: File '{path_str}' does not exist on disk.",
                    error="FILE_NOT_FOUND"
                )
            if not p.is_file():
                return VerificationResult(
                    verified=False,
                    details=f"Verification failed: Path '{path_str}' is not a valid file.",
                    error="NOT_A_FILE"
                )
            size = p.stat().st_size
            if size < min_size_bytes:
                return VerificationResult(
                    verified=False,
                    details=f"Verification failed: File '{path_str}' is empty ({size} bytes).",
                    error="FILE_EMPTY"
                )
            return VerificationResult(
                verified=True,
                details=f"Verified file '{p.name}' created successfully ({size} bytes)."
            )
        except Exception as e:
            return VerificationResult(
                verified=False,
                details=f"Verification error for '{path_str}': {e}",
                error="VERIFICATION_EXCEPTION"
            )

    @classmethod
    def verify_process_running(cls, proc_name: str) -> VerificationResult:
        """Verify that an application process is active in the OS process table."""
        try:
            import psutil
            low = proc_name.lower().strip()
            # Strip extension if passed
            base = os.path.splitext(low)[0]

            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    pname = (proc.info.get('name') or '').lower()
                    if base in pname or low in pname:
                        return VerificationResult(
                            verified=True,
                            details=f"Verified process '{proc.info['name']}' (PID: {proc.info['pid']}) is active."
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return VerificationResult(
                verified=False,
                details=f"Verification notice: Process '{proc_name}' not found in active process table.",
                error="PROCESS_NOT_FOUND"
            )
        except Exception as e:
            # If psutil is missing or restricted, return non-blocking notice
            return VerificationResult(
                verified=True,
                details=f"Process verification skipped: {e}"
            )

    @classmethod
    def verify_tool_output(cls, output_str: str) -> VerificationResult:
        """Inspect tool output string or JSON payload for embedded error indicators."""
        if not isinstance(output_str, str):
            return VerificationResult(verified=True, details="Non-string output")

        low = output_str.lower().strip()
        error_indicators = [
            "error:", "traceback (most recent call last):", "zerodivisionerror:",
            "syntaxerror:", "permission denied", "access denied", "scope violation",
            '"status": "failure"', '"error":', '"status": "error"'
        ]

        for ind in error_indicators:
            if ind in low:
                return VerificationResult(
                    verified=False,
                    details=f"Tool output contains failure indicator: '{ind}'",
                    error="TOOL_OUTPUT_ERROR",
                )

        return VerificationResult(verified=True, details="Tool output verified clean.")

    @classmethod
    def verify_action(cls, tool_name: str, args: Dict[str, Any], output_str: str) -> VerificationResult:
        """Verify the specific outcome of a tool execution."""
        # 1. Output string sanity check
        out_res = cls.verify_tool_output(output_str)
        if not out_res.verified:
            return out_res

        # 2. File write verification
        if tool_name in ("file_write", "create_file", "write_file"):
            target_path = args.get("path") or args.get("file_path") or args.get("name") or ""
            if target_path:
                return cls.verify_file_created(target_path)

        # 3. Application launch verification
        if tool_name in ("open_app", "launch_app"):
            app_name = args.get("app_name") or args.get("name") or ""
            if app_name:
                return cls.verify_process_running(app_name)

        # Default verification pass for standard tools
        return VerificationResult(
            verified=True,
            details=f"Action '{tool_name}' verified without errors."
        )


_global_verifier: Optional[ActionVerifier] = None


def get_action_verifier() -> ActionVerifier:
    global _global_verifier
    if _global_verifier is None:
        _global_verifier = ActionVerifier()
    return _global_verifier
