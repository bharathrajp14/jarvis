# tools/tool_result.py — BR JARVIS Canonical Tool Evidence & Result Contract
"""
Canonical unified ToolResult contract for BR JARVIS MK40.2 / MK41.
Every tool execution produces a structured ToolResult. Never guess success — always observe and verify.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from .domain import Observation, ToolErrorCode, ToolExecutionStatus

# Backward compatibility alias
ToolStatus = ToolExecutionStatus


# ── Error indicator patterns for legacy output parsing ────────────────────────
_ERROR_PATTERNS = [
    r"\berror\b",
    r"\bfailed\b",
    r"\btraceback\b",
    r"permission denied",
    r"access denied",
    r"not found",
    r"no such file",
    r"exception",
    r"syntaxerror",
    r"zerodivisionerror",
    r'"status"\s*:\s*"(?:fail|error)"',
    r"err_file_not_found",
    r"error building document",
    r"unauthorized",
    r"authentication required",
]
_ERROR_RE = re.compile("|".join(_ERROR_PATTERNS), re.IGNORECASE)

_BLOCKED_PATTERNS = [
    r"permission denied",
    r"access denied",
    r"blocked by policy",
    r"not permitted",
    r"unauthorized",
    r"scope violation",
]
_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)

_REQUIRES_USER_PATTERNS = [
    r"requires_user",
    r"waiting for user",
    r"requires approval",
    r"captcha",
    r"please unlock",
    r"pin required",
    r"authentication required",
]
_REQUIRES_USER_RE = re.compile("|".join(_REQUIRES_USER_PATTERNS), re.IGNORECASE)


class _HybridSuccessAccessor:
    """Hybrid descriptor allowing ToolResult.success(...) classmethod and res.success bool property."""

    def __init__(self, func: Callable):
        self.func = func

    def __get__(self, instance, owner=None):
        if instance is None:
            return self.func.__get__(owner, owner)
        return instance.status == ToolExecutionStatus.SUCCESS

    def __set__(self, instance, value):
        pass


class _HybridFailedAccessor:
    """Hybrid descriptor allowing ToolResult.failed(...) classmethod and res.failed bool property."""

    def __init__(self, func: Callable):
        self.func = func

    def __get__(self, instance, owner=None):
        if instance is None:
            return self.func.__get__(owner, owner)
        return instance.status == ToolExecutionStatus.FAILED

    def __set__(self, instance, value):
        pass


@dataclass
class ToolResult:
    """
    Canonical unified result contract returned by all tool invocations.
    Carries structured payload, verifiable evidence, timing, observation, and factual status.
    """

    tool_name: str
    status: ToolExecutionStatus = ToolExecutionStatus.SUCCESS
    task_id: str = ""
    step_id: str = ""
    invocation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    data: Any = None  # Structured return payload
    evidence: str = ""  # Physical proof string
    verified: bool = False  # True if physically verified
    error_code: Optional[Union[str, ToolErrorCode]] = None
    message: str = ""  # Human-readable summary
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_ms: float = 0.0
    observation: Optional[Observation] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    # ── Backward Compatibility Properties ──────────────────────────────────────

    @property
    def is_success(self) -> bool:
        return self.status == ToolExecutionStatus.SUCCESS

    @property
    def is_verified(self) -> bool:
        return self.verified

    @property
    def is_blocked(self) -> bool:
        return self.status in (
            ToolExecutionStatus.BLOCKED,
            ToolExecutionStatus.DENIED,
            ToolExecutionStatus.REQUIRES_APPROVAL,
        )

    def __contains__(self, item: Any) -> bool:
        """Support 'needle in tool_result' substring and key lookups."""
        needle = str(item).lower()
        if needle in self.output.lower():
            return True
        if self.data is not None:
            if isinstance(self.data, dict) and item in self.data:
                return True
            if needle in str(self.data).lower():
                return True
        if self.message and needle in self.message.lower():
            return True
        if self.evidence and needle in self.evidence.lower():
            return True
        return False

    def __str__(self) -> str:
        return self.output

    @property
    def output(self) -> str:
        """String representation of stdout or payload for textual agents."""
        if self.stdout:
            return self.stdout
        if self.data is not None:
            if isinstance(self.data, str):
                return self.data
            try:
                return json.dumps(self.data, indent=2, default=str)
            except Exception:
                return str(self.data)
        return self.message or ("Success" if self.is_success else "Failed")

    @property
    def error(self) -> Optional[str]:
        if self.error_code:
            code_str = self.error_code.value if hasattr(self.error_code, "value") else str(self.error_code)
            return f"{code_str}: {self.message}" if self.message else code_str
        return self.message if not self.is_success else None

    @property
    def duration_seconds(self) -> float:
        return self.execution_ms / 1000.0

    @property
    def duration(self) -> float:
        return self.execution_ms / 1000.0

    @property
    def duration_ms(self) -> float:
        return self.execution_ms

    @property
    def tool(self) -> str:
        return self.tool_name

    @property
    def execution_id(self) -> str:
        return self.invocation_id

    @property
    def verification_status(self) -> ToolExecutionStatus:
        return ToolExecutionStatus.SUCCESS if self.verified else self.status

    # ── String Serialization for Agents / LLMs ─────────────────────────────────

    def to_agent_str(self) -> str:
        """
        Produce a clean, deterministic string representation for the ReAct/Agent loop.
        Includes status tag, evidence, and primary data.
        """
        if self.status == ToolExecutionStatus.SUCCESS:
            body = self.output
            # If body is a clean scalar number/bool or evidence is already implicit, return clean body
            if body and (body.strip().lstrip("-").isdigit() or body.strip().lower() in ("true", "false")):
                return body.strip()
            if self.evidence and self.evidence not in body and not self.evidence.startswith("Action '"):
                return f"[SUCCESS_VERIFIED] {self.evidence}\n{body}".strip()
            return body or f"[SUCCESS] {self.tool_name} completed."

        elif self.status == ToolExecutionStatus.REQUIRES_APPROVAL:
            return f"[APPROVAL_REQUIRED] {self.message or 'Action requires user confirmation.'}"

        elif self.status in (ToolExecutionStatus.BLOCKED, ToolExecutionStatus.DENIED):
            return f"[BLOCKED] {self.error or 'Operation blocked by security policy.'}"

        elif self.status == ToolExecutionStatus.TIMEOUT:
            return f"[TIMEOUT] {self.tool_name} exceeded timeout limit ({self.execution_ms:.0f}ms)."

        elif self.status == ToolExecutionStatus.NOT_FOUND:
            return f"[NOT_FOUND] Unknown tool '{self.tool_name}'."

        elif self.status == ToolExecutionStatus.NOT_AVAILABLE:
            return f"[NOT_AVAILABLE] Tool '{self.tool_name}' is not available: {self.message}"

        elif self.status == ToolExecutionStatus.VERIFICATION_FAILED:
            return f"[VERIFICATION_FAILED] {self.message or 'Physical verification mismatch'}\n{self.stderr or self.output}".strip()

        else:
            return f"[FAILED] Tool '{self.tool_name}' failed: {self.error or self.message or self.stderr}".strip()

    def to_dict(self) -> Dict[str, Any]:
        """Produce clean JSON serializable dictionary."""
        return {
            "tool_name": self.tool_name,
            "tool": self.tool_name,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "invocation_id": self.invocation_id,
            "execution_id": self.invocation_id,
            "status": self.status.value,
            "success": self.is_success,
            "data": self.data,
            "output": self.output,
            "evidence": self.evidence,
            "verified": self.verified,
            "error_code": self.error_code.value if hasattr(self.error_code, "value") else self.error_code,
            "error": self.error,
            "message": self.message,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "execution_ms": self.execution_ms,
            "duration_seconds": self.duration_seconds,
            "observation": self.observation.to_dict() if self.observation else None,
            "artifacts": self.artifacts,
            "warnings": self.warnings,
            "side_effects": self.side_effects,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    # ── Factories ──────────────────────────────────────────────────────────────

    @classmethod
    def _create_success(
        cls,
        tool_name: str,
        data: Any = None,
        output: str = "",
        evidence: str = "",
        verified: bool = True,
        observation: Optional[Observation] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        side_effects: Optional[List[str]] = None,
        execution_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        """Factory for verified successful executions."""
        out_str = output or (
            json.dumps(data, indent=2, default=str) if isinstance(data, (dict, list)) else str(data or "")
        )
        return cls(
            tool_name=tool_name,
            status=ToolExecutionStatus.SUCCESS,
            data=data if data is not None else out_str,
            stdout=out_str,
            evidence=evidence or (f"Verified {tool_name}" if verified else ""),
            verified=verified,
            observation=observation,
            artifacts=artifacts or [],
            side_effects=side_effects or [],
            execution_ms=execution_ms,
            metadata=metadata or {},
        )

    @classmethod
    def _create_failed(
        cls,
        tool_name: str,
        error_code: Union[str, ToolErrorCode] = ToolErrorCode.EXECUTION_EXCEPTION,
        message: str = "",
        stderr: str = "",
        return_code: int = 1,
        execution_ms: float = 0.0,
        data: Any = None,
    ) -> "ToolResult":
        """Factory for failed executions."""
        return cls(
            tool_name=tool_name,
            status=ToolExecutionStatus.FAILED,
            error_code=error_code,
            message=message or str(error_code),
            stderr=stderr or message,
            return_code=return_code,
            verified=False,
            execution_ms=execution_ms,
            data=data,
        )

    # Attach hybrid descriptors
    success = _HybridSuccessAccessor(_create_success)
    failed = _HybridFailedAccessor(_create_failed)

    @classmethod
    def blocked(
        cls,
        tool_name: str,
        reason: str = "Blocked by security policy",
        error_code: ToolErrorCode = ToolErrorCode.POLICY_DENIED,
    ) -> "ToolResult":
        """Factory for blocked / denied actions."""
        return cls(
            tool_name=tool_name,
            status=ToolExecutionStatus.BLOCKED,
            error_code=error_code,
            message=reason,
            verified=False,
        )

    @classmethod
    def requires_approval(
        cls,
        tool_name: str,
        reason: str = "Action requires user confirmation",
        data: Any = None,
    ) -> "ToolResult":
        """Factory for operations halted pending human approval."""
        return cls(
            tool_name=tool_name,
            status=ToolExecutionStatus.REQUIRES_APPROVAL,
            error_code=ToolErrorCode.APPROVAL_REQUIRED,
            message=reason,
            data=data,
            verified=False,
        )

    @classmethod
    def timeout(
        cls,
        tool_name: str,
        timeout_sec: float,
        execution_ms: float = 0.0,
    ) -> "ToolResult":
        """Factory for timed-out actions."""
        return cls(
            tool_name=tool_name,
            status=ToolExecutionStatus.TIMEOUT,
            error_code=ToolErrorCode.TIMEOUT_EXCEEDED,
            message=f"Tool '{tool_name}' timed out after {timeout_sec:.1f}s",
            execution_ms=execution_ms or (timeout_sec * 1000.0),
            verified=False,
        )

    @classmethod
    def not_found(cls, tool_name: str) -> "ToolResult":
        """Factory for missing tools."""
        return cls(
            tool_name=tool_name,
            status=ToolExecutionStatus.NOT_FOUND,
            error_code=ToolErrorCode.TOOL_NOT_FOUND,
            message=f"Tool '{tool_name}' is not registered in the catalog.",
            verified=False,
        )

    @classmethod
    def from_raw_output(
        cls,
        tool_name: str,
        raw_output: Any,
        duration_seconds: float = 0.0,
        return_code: int = 0,
        stderr: str = "",
        verified: bool = False,
    ) -> "ToolResult":
        """Bridge raw output or string from legacy tools into the canonical ToolResult contract."""
        if isinstance(raw_output, ToolResult):
            return raw_output

        exec_ms = duration_seconds * 1000.0
        if isinstance(raw_output, dict):
            status_val = str(raw_output.get("status", "")).upper()
            if status_val in ToolExecutionStatus._value2member_map_:
                status = ToolExecutionStatus(status_val)
            elif raw_output.get("success") is True:
                status = ToolExecutionStatus.SUCCESS
            elif raw_output.get("success") is False:
                status = ToolExecutionStatus.FAILED
            else:
                status = ToolExecutionStatus.SUCCESS if return_code == 0 else ToolExecutionStatus.FAILED

            return cls(
                tool_name=tool_name,
                status=status,
                data=raw_output,
                stdout=json.dumps(raw_output, indent=2, default=str),
                stderr=stderr or str(raw_output.get("error", "")),
                return_code=return_code,
                execution_ms=exec_ms,
                evidence=str(raw_output.get("evidence", "")),
                verified=bool(raw_output.get("verified", verified)),
                message=str(raw_output.get("message", "")),
            )

        str_output = str(raw_output or "")
        if return_code != 0:
            status = ToolExecutionStatus.FAILED
            error_code = ToolErrorCode.EXECUTION_EXCEPTION
            err_msg = stderr or f"Non-zero return code {return_code}"
        elif _BLOCKED_RE.search(str_output):
            status = ToolExecutionStatus.BLOCKED
            error_code = ToolErrorCode.POLICY_DENIED
            err_msg = str_output[:200]
        elif _REQUIRES_USER_RE.search(str_output):
            status = ToolExecutionStatus.REQUIRES_APPROVAL
            error_code = ToolErrorCode.APPROVAL_REQUIRED
            err_msg = str_output[:200]
        elif _ERROR_RE.search(str_output) and not str_output.startswith("[SUCCESS_VERIFIED]"):
            status = ToolExecutionStatus.FAILED
            error_code = ToolErrorCode.EXECUTION_EXCEPTION
            err_msg = str_output[:200]
        else:
            status = ToolExecutionStatus.SUCCESS
            error_code = None
            err_msg = ""

        return cls(
            tool_name=tool_name,
            status=status,
            data=str_output,
            stdout=str_output,
            stderr=stderr,
            return_code=return_code,
            execution_ms=exec_ms,
            error_code=error_code,
            message=err_msg,
            verified=verified or (status == ToolExecutionStatus.SUCCESS and bool(str_output.strip())),
        )
