# tools/tool_result.py — BR JARVIS MK40.2 Tool Evidence Contract
"""
Every tool execution must produce a ToolResult, not a raw string.

The ToolResult carries:
  - Observed status (SUCCESS / FAILED / PARTIAL / BLOCKED / TIMEOUT / UNAVAILABLE /
                     REQUIRES_USER / UNVERIFIED)
  - Actual stdout and stderr from the operation
  - Duration in seconds
  - Side effects (files created, processes started, commits pushed, etc.)
  - Evidence string (machine-verifiable proof of the claimed state)
  - Verification status (set by the verifier after fact-checking)

This is the §5 Tool Evidence Contract from BR JARVIS MK40.2 spec.
"""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Status vocabulary ─────────────────────────────────────────────────────────

class ToolStatus(str, Enum):
    SUCCESS        = "SUCCESS"
    FAILED         = "FAILED"
    PARTIAL        = "PARTIAL"
    BLOCKED        = "BLOCKED"
    TIMEOUT        = "TIMEOUT"
    UNAVAILABLE    = "UNAVAILABLE"
    REQUIRES_USER  = "REQUIRES_USER"
    UNVERIFIED     = "UNVERIFIED"


# ── Error indicator patterns used to auto-detect failures in raw string output ─

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

# Patterns that indicate the tool was blocked by a permission/policy layer
_BLOCKED_PATTERNS = [
    r"permission denied",
    r"access denied",
    r"blocked by policy",
    r"not permitted",
    r"unauthorized",
    r"scope violation",
]
_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)

# Patterns that indicate user action is required
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


# ── ToolResult dataclass ──────────────────────────────────────────────────────

@dataclass
class ToolResult:
    """
    Structured result from a tool execution. Never guess success — always observe.

    The `status` field is the canonical verdict. It must be set by the executor
    or the registry wrapper — never assumed to be SUCCESS merely because no
    exception was raised.
    """
    tool_name:           str
    status:              ToolStatus = ToolStatus.UNVERIFIED
    output:              str = ""          # primary text output (stdout equivalent)
    stderr:              str = ""
    return_code:         int = 0
    duration_seconds:    float = 0.0
    side_effects:        List[str] = field(default_factory=list)
    evidence:            str = ""          # concise proof: "File exists at /path (4,231 bytes)"
    verification_status: ToolStatus = ToolStatus.UNVERIFIED
    error:               Optional[str] = None
    metadata:            Dict[str, Any] = field(default_factory=dict)
    timestamp:           float = field(default_factory=time.time)

    # ── Convenience accessors ──────────────────────────────────────────────────

    @property
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    @property
    def is_verified(self) -> bool:
        return self.verification_status == ToolStatus.SUCCESS

    @property
    def is_blocked(self) -> bool:
        return self.status in (ToolStatus.BLOCKED, ToolStatus.REQUIRES_USER, ToolStatus.UNAVAILABLE)

    # ── Factories ──────────────────────────────────────────────────────────────

    @classmethod
    def from_raw_output(
        cls,
        tool_name: str,
        raw_output: str,
        duration_seconds: float = 0.0,
        return_code: int = 0,
        stderr: str = "",
    ) -> "ToolResult":
        """
        Parse a raw string output from a legacy tool and infer the ToolStatus.

        This bridges older tools that return plain strings so they can participate
        in the evidence contract without requiring immediate refactoring.
        """
        output = raw_output or ""

        # Determine status from output content
        if return_code != 0:
            status = ToolStatus.FAILED
            error = f"Non-zero return code: {return_code}"
        elif _BLOCKED_RE.search(output):
            status = ToolStatus.BLOCKED
            error = f"Blocked: {output[:200]}"
        elif _REQUIRES_USER_RE.search(output):
            status = ToolStatus.REQUIRES_USER
            error = None
        elif _ERROR_RE.search(output):
            status = ToolStatus.FAILED
            error = f"Error pattern in output: {output[:200]}"
        elif not output.strip():
            # Empty output is ambiguous — treat as UNVERIFIED, not SUCCESS
            status = ToolStatus.UNVERIFIED
            error = None
        else:
            status = ToolStatus.SUCCESS
            error = None

        return cls(
            tool_name=tool_name,
            status=status,
            output=output,
            stderr=stderr,
            return_code=return_code,
            duration_seconds=duration_seconds,
            error=error,
        )

    @classmethod
    def success(
        cls,
        tool_name: str,
        output: str = "",
        evidence: str = "",
        side_effects: Optional[List[str]] = None,
        duration_seconds: float = 0.0,
    ) -> "ToolResult":
        """Factory for a known-good result."""
        return cls(
            tool_name=tool_name,
            status=ToolStatus.SUCCESS,
            verification_status=ToolStatus.SUCCESS,
            output=output,
            evidence=evidence or output[:200],
            side_effects=side_effects or [],
            duration_seconds=duration_seconds,
        )

    @classmethod
    def failed(
        cls,
        tool_name: str,
        error: str,
        output: str = "",
        duration_seconds: float = 0.0,
    ) -> "ToolResult":
        """Factory for a known-bad result."""
        return cls(
            tool_name=tool_name,
            status=ToolStatus.FAILED,
            verification_status=ToolStatus.FAILED,
            output=output,
            error=error,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def blocked(
        cls,
        tool_name: str,
        reason: str,
    ) -> "ToolResult":
        """Factory for a blocked result (permission / policy)."""
        return cls(
            tool_name=tool_name,
            status=ToolStatus.BLOCKED,
            verification_status=ToolStatus.BLOCKED,
            error=reason,
            output=f"BLOCKED: {reason}",
        )

    @classmethod
    def unavailable(cls, tool_name: str, reason: str = "") -> "ToolResult":
        """Factory for a tool that is not registered or has missing dependencies."""
        return cls(
            tool_name=tool_name,
            status=ToolStatus.UNAVAILABLE,
            verification_status=ToolStatus.UNAVAILABLE,
            error=reason or f"Tool '{tool_name}' is not available on this system.",
            output=f"UNAVAILABLE: {tool_name}",
        )

    @classmethod
    def requires_user(cls, tool_name: str, prompt: str) -> "ToolResult":
        """Factory for operations that need human input to proceed."""
        return cls(
            tool_name=tool_name,
            status=ToolStatus.REQUIRES_USER,
            verification_status=ToolStatus.REQUIRES_USER,
            output=prompt,
            error=None,
        )

    # ── Serialisation ──────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["verification_status"] = self.verification_status.value
        return d

    def to_ledger_side_effects(self) -> List[str]:
        """
        Return side_effects augmented with any evidence text, ready to
        store in the ExecutionLedger.
        """
        effects = list(self.side_effects)
        return effects
