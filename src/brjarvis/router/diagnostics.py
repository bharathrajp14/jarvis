# router/diagnostics.py — Structured Backend Diagnostics & Error Classification for BR JARVIS
from __future__ import annotations

"""
Comprehensive structured diagnostic subsystem for multi-backend execution.
Classifies all model, provider, network, and tool failures into distinct FailureType categories,
strips credentials from diagnostic traces, and generates user-facing and developer-facing reports.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("JARVIS.Router.Diagnostics")


class FailureType(str, Enum):
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    AUTH_FAILURE = "AUTH_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_TOOL_SCHEMA = "INVALID_TOOL_SCHEMA"
    UNSUPPORTED_MODALITY = "UNSUPPORTED_MODALITY"
    CONTEXT_TOO_LARGE = "CONTEXT_TOO_LARGE"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    PARSER_ERROR = "PARSER_ERROR"
    TOOL_ERROR = "TOOL_ERROR"
    POLICY_DENIED = "POLICY_DENIED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Transient failure types eligible for bounded retry with exponential backoff
TRANSIENT_FAILURE_TYPES = frozenset(
    {
        FailureType.RATE_LIMIT,
        FailureType.QUOTA_EXCEEDED,
        FailureType.NETWORK_ERROR,
        FailureType.TIMEOUT,
        FailureType.PROVIDER_ERROR,
    }
)


# Regex patterns to sanitize sensitive credentials from error logs and traces
_SECRET_PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"(sk-[A-Za-z0-9_\-]{16,})", re.IGNORECASE),
    re.compile(r"(AQ\.[A-Za-z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(AIza[0-9A-Za-z-_]{35})", re.IGNORECASE),
    re.compile(r"(key=)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"(api_key['\":\s=]+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"(token['\":\s=]+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"([0-9]{9,11}:[A-Za-z0-9_\-]{30,})"),  # Telegram bot tokens
]


def sanitize_diagnostic_text(text: str) -> str:
    """Scrub all API keys, bearer tokens, and secrets from diagnostic messages."""
    if not text:
        return ""
    sanitized = str(text)
    for pat in _SECRET_PATTERNS:
        sanitized = pat.sub(r"\1[REDACTED_SECRET]", sanitized)
    return sanitized


@dataclass
class BackendAttempt:
    provider: str
    model: str
    status: str  # "SUCCESS", "FAILED", "RETRYING"
    stage: str  # "provider_request", "tool_call_normalization", "model_routing", "output_parsing"
    error_type: FailureType
    error: str
    latency_ms: int = 0
    http_status: Optional[int] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "stage": self.stage,
            "error_type": self.error_type.value if hasattr(self.error_type, "value") else str(self.error_type),
            "error": sanitize_diagnostic_text(self.error),
            "latency_ms": self.latency_ms,
            "http_status": self.http_status,
            "timestamp": self.timestamp,
        }


@dataclass
class TaskExecutionDiagnostic:
    trace_id: str
    task_id: str
    goal: str
    attempts: list[BackendAttempt] = field(default_factory=list)
    final_reason: str = "ALL_BACKENDS_FAILED"
    recovery_action: str = "NONE"
    user_friendly_message: str = ""

    def add_attempt(self, attempt: BackendAttempt) -> None:
        self.attempts.append(attempt)

    def format_developer_trace(self) -> str:
        """Format full structured diagnostic trace for developer inspection and logs."""
        lines = [
            "=== TASK_EXECUTION_FAILED ===",
            f"trace_id: {self.trace_id}",
            f"task_id:  {self.task_id}",
            f"goal:     {self.goal[:120]}...",
            "",
            f"Backend attempts ({len(self.attempts)}):",
        ]
        for idx, att in enumerate(self.attempts, 1):
            lines.append(f"  {idx}.")
            lines.append(f"    provider:   {att.provider}")
            lines.append(f"    model:      {att.model}")
            lines.append(f"    status:     {att.status}")
            lines.append(f"    stage:      {att.stage}")
            lines.append(
                f"    error_type: {att.error_type.value if hasattr(att.error_type, 'value') else att.error_type}"
            )
            lines.append(f"    error:      {sanitize_diagnostic_text(att.error)}")
            lines.append(f"    latency:    {att.latency_ms}ms")
            if att.http_status:
                lines.append(f"    http_code:  {att.http_status}")
        lines.append("")
        lines.append(f"Final reason: {self.final_reason}")
        lines.append(f"Recovery:     {self.recovery_action}")
        return "\n".join(lines)

    def format_user_facing_summary(self) -> str:
        """Format clear, polite, non-technical explanation for speech synthesis and chat HUD."""
        if not self.attempts:
            return "I was unable to complete your request because no AI backend models are currently configured or available."

        unique_errors = []
        for att in self.attempts:
            err_label = att.error_type.value.replace("_", " ").title()
            summary = f"{att.provider} ({err_label})"
            if summary not in unique_errors:
                unique_errors.append(summary)

        err_list_str = ", and ".join(unique_errors)
        return (
            f"I couldn't complete the planning stage because all compatible AI providers failed. "
            f"Attempted: {err_list_str}. "
            f"Please check network connectivity or your local proxy gateway."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "goal": self.goal,
            "attempts": [a.to_dict() for a in self.attempts],
            "final_reason": self.final_reason,
            "recovery_action": self.recovery_action,
            "user_friendly_message": self.user_friendly_message,
        }


def classify_exception(exc: Exception, http_status: Optional[int] = None) -> tuple[FailureType, str]:
    """Inspect exception message, class name, and HTTP status code to return granular FailureType."""
    if exc is None:
        return FailureType.INTERNAL_ERROR, "Unknown error"

    msg = str(exc)
    exc_type = type(exc).__name__
    combined = f"{exc_type}: {msg}".lower()

    # 1. Timeout detection
    if any(
        k in combined
        for k in ("timeout", "timed out", "timeouterror", "deadline exceeded", "readtimeout", "connecttimeout")
    ):
        return FailureType.TIMEOUT, sanitize_diagnostic_text(msg)

    # 2. Rate limits & Quotas
    if http_status == 429 or any(k in combined for k in ("429", "rate limit", "ratelimit", "too many requests")):
        return FailureType.RATE_LIMIT, sanitize_diagnostic_text(msg)
    if any(k in combined for k in ("quota", "resource_exhausted", "insufficient_quota", "credit balance")):
        return FailureType.QUOTA_EXCEEDED, sanitize_diagnostic_text(msg)

    # 3. Authentication & Authorization
    if http_status in (401, 403) or any(
        k in combined
        for k in (
            "unauthorized",
            "invalid api key",
            "auth_error",
            "forbidden",
            "permission denied",
            "access denied",
            "authentication",
        )
    ):
        return FailureType.AUTH_FAILURE, sanitize_diagnostic_text(msg)

    # 4. Context too large
    if any(
        k in combined
        for k in (
            "context length",
            "maximum context",
            "token limit",
            "prompt is too long",
            "too many tokens",
            "exceeds context window",
        )
    ):
        return FailureType.CONTEXT_TOO_LARGE, sanitize_diagnostic_text(msg)

    # 5. Network / Connection errors
    if any(
        k in combined
        for k in (
            "connection refused",
            "connection error",
            "connecterror",
            "remotedisconnected",
            "failed to establish a new connection",
            "socket.error",
            "network unreachable",
        )
    ):
        return FailureType.NETWORK_ERROR, sanitize_diagnostic_text(msg)

    # 6. Model unavailable / Not found
    if http_status == 404 or any(
        k in combined for k in ("model not found", "model unavailable", "does not exist", "unsupported model")
    ):
        return FailureType.MODEL_UNAVAILABLE, sanitize_diagnostic_text(msg)

    # 7. Invalid tool schema / Parsing error
    if any(
        k in combined
        for k in ("invalid tool schema", "schema validation error", "tools parameter invalid", "function schema")
    ):
        return FailureType.INVALID_TOOL_SCHEMA, sanitize_diagnostic_text(msg)
    if any(k in combined for k in ("jsondecodeerror", "parsererror", "failed to parse", "invalid json")):
        return FailureType.PARSER_ERROR, sanitize_diagnostic_text(msg)

    # 8. Modality / Vision unsupported
    if any(k in combined for k in ("unsupported modality", "image input not supported", "vision not supported")):
        return FailureType.UNSUPPORTED_MODALITY, sanitize_diagnostic_text(msg)

    # 9. Invalid request
    if http_status == 400 or any(k in combined for k in ("bad request", "invalid argument", "invalid_request_error")):
        return FailureType.INVALID_REQUEST, sanitize_diagnostic_text(msg)

    # 10. Provider / 5xx error
    if (http_status and http_status >= 500) or any(
        k in combined
        for k in ("internal server error", "502 bad gateway", "503 service unavailable", "504 gateway timeout")
    ):
        return FailureType.PROVIDER_ERROR, sanitize_diagnostic_text(msg)

    return FailureType.PROVIDER_ERROR, sanitize_diagnostic_text(msg)
