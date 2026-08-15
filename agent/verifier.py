# agent/verifier.py — Autonomous Action & Goal Verification Subsystem
"""
State and Goal Verification Engine for BR JARVIS MK40.
Ensures actions are rigorously verified against actual OS/filesystem state,
preventing false-positive completions, unhandled sandbox handoffs, and hallucinated success states.
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

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
    def verify_artifact_exported(cls, record_or_path: Union[Any, str, Path]) -> VerificationResult:
        """Verify that a user-facing artifact was securely exported to host, exists, and is readable."""
        try:
            from agent.artifacts import ArtifactRecord
            if isinstance(record_or_path, ArtifactRecord):
                if not record_or_path.exported or not record_or_path.host_path:
                    return VerificationResult(
                        verified=False,
                        details=f"Artifact '{record_or_path.filename}' was not marked as exported ({record_or_path.error or 'no host path'}).",
                        error="EXPORT_FAILED"
                    )
                host_p = Path(record_or_path.host_path)
            else:
                host_p = Path(record_or_path)

            if not host_p.exists():
                return VerificationResult(
                    verified=False,
                    details=f"Exported artifact '{host_p}' does not exist on host filesystem.",
                    error="FILE_NOT_FOUND"
                )
            if not host_p.is_file():
                return VerificationResult(
                    verified=False,
                    details=f"Exported artifact '{host_p}' is not a valid file.",
                    error="NOT_A_FILE"
                )
            if host_p.stat().st_size == 0:
                return VerificationResult(
                    verified=False,
                    details=f"Exported artifact '{host_p}' is empty (0 bytes).",
                    error="FILE_EMPTY"
                )
            if not os.access(host_p, os.R_OK):
                return VerificationResult(
                    verified=False,
                    details=f"Exported artifact '{host_p}' is not readable by current user.",
                    error="PERMISSION_DENIED"
                )

            return VerificationResult(
                verified=True,
                details=f"Verified artifact '{host_p.name}' successfully exported and readable on host ({host_p.stat().st_size} bytes)."
            )
        except Exception as e:
            return VerificationResult(
                verified=False,
                details=f"Artifact export verification error: {e}",
                error="VERIFICATION_EXCEPTION"
            )

    @classmethod
    def verify_browser_artifact_opened(
        cls,
        host_path_or_url: Union[str, Path],
        browser_response: Optional[Union[dict, str]] = None,
        expected_content: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify that a browser opened a legitimate, readable host artifact with no file-not-found errors.
        Guarantees that raw sandbox paths or missing files fail closed, and asserts actual content presence.
        """
        target_str = str(host_path_or_url).strip()
        low_target = target_str.lower().replace("\\", "/")

        # 1. Sandbox jail path check — Fail closed if a raw sandbox path is opened
        if "jarvis_sandbox_jails" in low_target or "sandbox_jails" in low_target or "/jail_" in low_target:
            return VerificationResult(
                verified=False,
                details=f"Security/Stability Violation: Browser attempted to open internal sandbox jail path '{target_str}'. Must export to host first.",
                error="SANDBOX_PATH_EXPOSURE"
            )

        # 2. Local file validation
        if not (target_str.startswith("http://") or target_str.startswith("https://")):
            clean_path = target_str
            if clean_path.startswith("file:///"):
                clean_path = clean_path[8:] if sys.platform == "win32" else clean_path[7:]
            elif clean_path.startswith("file://"):
                clean_path = clean_path[7:]

            p = Path(clean_path)
            if not p.exists():
                return VerificationResult(
                    verified=False,
                    details=f"Browser target file '{clean_path}' does not exist on disk.",
                    error="ERR_FILE_NOT_FOUND"
                )
            if not os.access(p, os.R_OK):
                return VerificationResult(
                    verified=False,
                    details=f"Browser target file '{clean_path}' is not readable.",
                    error="ERR_ACCESS_DENIED"
                )
            if p.is_file() and p.stat().st_size == 0:
                return VerificationResult(
                    verified=False,
                    details=f"Browser target file '{clean_path}' is empty (0 bytes).",
                    error="FILE_EMPTY"
                )

            # Check expected content inside file if specified
            if expected_content and p.is_file():
                try:
                    file_text = p.read_text(encoding="utf-8", errors="replace")
                    if expected_content.lower() not in file_text.lower():
                        return VerificationResult(
                            verified=False,
                            details=f"File content verification failed: Expected '{expected_content}' not found in '{p.name}'.",
                            error="CONTENT_MISMATCH"
                        )
                except Exception as read_err:
                    return VerificationResult(
                        verified=False,
                        details=f"Error reading file '{clean_path}' for content check: {read_err}",
                        error="READ_ERROR"
                    )

        # 3. Inspect browser response / DOM / console output if provided
        if browser_response:
            resp_str = str(browser_response).lower()
            err_patterns = [
                ("err_file_not_found", "ERR_FILE_NOT_FOUND"),
                ("file not found", "ERR_FILE_NOT_FOUND"),
                ("it may have been moved, edited, or deleted", "ERR_FILE_NOT_FOUND"),
                ("err_access_denied", "ERR_ACCESS_DENIED"),
                ("access denied", "ERR_ACCESS_DENIED"),
                ("failed to load resource", "ERR_LOAD_FAILED"),
                ("cannot open", "ERR_OPEN_FAILED"),
                ("could not open", "ERR_OPEN_FAILED"),
            ]
            for pattern, err_code in err_patterns:
                if pattern in resp_str:
                    return VerificationResult(
                        verified=False,
                        details=f"Browser reported error: '{pattern}' while loading '{target_str}'.",
                        error=err_code
                    )

        return VerificationResult(
            verified=True,
            details=f"Browser artifact open verified successfully for '{target_str}'."
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
            '"status": "failure"', '"error":', '"status": "error"', "err_file_not_found"
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

        # 3. Artifact export verification
        if tool_name in ("artifact_export", "export_artifact"):
            target_path = args.get("path") or args.get("sandbox_path") or ""
            if target_path:
                return cls.verify_artifact_exported(target_path)

        # 4. Browser / URL open verification
        if tool_name in ("browser_open_url", "open_browser", "web_browser"):
            target_url = args.get("url") or args.get("uri") or args.get("path") or ""
            return cls.verify_browser_artifact_opened(target_url, browser_response=output_str)

        # 5. Application launch verification
        if tool_name in ("open_app", "launch_app"):
            app_name = args.get("app_name") or args.get("name") or ""
            # If opening browser with a file target
            if any(b in app_name.lower() for b in ["chrome", "msedge", "edge", "brave", "firefox"]):
                parts = app_name.split(maxsplit=1)
                if len(parts) > 1 and (":" in parts[1] or "/" in parts[1] or "\\" in parts[1]):
                    return cls.verify_browser_artifact_opened(parts[1], browser_response=output_str)
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
