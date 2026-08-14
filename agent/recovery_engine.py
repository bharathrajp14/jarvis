# agent/recovery_engine.py — Standardized Failure Classification & Recovery Engine
"""
Standardized failure categorization, stuck-task detection, tool-call deduplication,
exponential backoff, and automatic replanning for Autonomous Agent 2.0.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.RecoveryEngine")


class FailureCategory(str, Enum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    APP_NOT_INSTALLED = "APP_NOT_INSTALLED"
    APP_CRASHED = "APP_CRASHED"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    USER_APPROVAL_REQUIRED = "USER_APPROVAL_REQUIRED"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


@dataclass
class FailureAnalysis:
    category: FailureCategory
    message: str
    suggested_action: str  # "retry", "replan", "fallback", "pause_for_user", "abort"
    retry_allowed: bool
    backoff_seconds: float
    details: Dict[str, Any]


class RecoveryEngine:
    """Classifies execution errors and produces deterministic recovery plans."""

    def __init__(self, max_consecutive_duplicates: int = 3, max_step_retries: int = 3):
        self.max_consecutive_duplicates = max_consecutive_duplicates
        self.max_step_retries = max_step_retries
        self._action_call_history: List[Tuple[str, str, float]] = []  # (tool_name, params_hash, timestamp)

    def analyze_failure(self, tool_name: str, error_text: str, context: Optional[Dict[str, Any]] = None) -> FailureAnalysis:
        err = (error_text or "").lower()
        ctx = context or {}

        # 1. User Auth / PIN / Biometric / Captcha
        if "captcha" in err or "recaptcha" in err or "cloudflare" in err or "bot detection" in err:
            return FailureAnalysis(
                category=FailureCategory.CAPTCHA_REQUIRED,
                message="Human verification or CAPTCHA detected on screen/page.",
                suggested_action="pause_for_user",
                retry_allowed=False,
                backoff_seconds=0.0,
                details={"requires_user": True, "prompt": "Please complete the CAPTCHA or verification challenge on your screen/browser."},
            )

        if "locked" in err or "pin required" in err or "biometric" in err or "waiting_for_user_authentication" in err:
            return FailureAnalysis(
                category=FailureCategory.AUTH_REQUIRED,
                message="Device or account authentication required.",
                suggested_action="pause_for_user",
                retry_allowed=False,
                backoff_seconds=0.0,
                details={"requires_user": True, "prompt": "Please unlock your device or authorize the session."},
            )

        # 2. Permission Denied
        if "permission denied" in err or "not permitted" in err or "blocked by policy" in err or "unauthorized" in err:
            return FailureAnalysis(
                category=FailureCategory.PERMISSION_DENIED,
                message=f"Action '{tool_name}' blocked by security permission policy.",
                suggested_action="pause_for_user" if "approval" in err else "replan",
                retry_allowed=False,
                backoff_seconds=0.0,
                details={"tool": tool_name},
            )

        # 3. Device Offline / Connection
        if "device offline" in err or "device unreachable" in err or "no mobile session" in err:
            return FailureAnalysis(
                category=FailureCategory.DEVICE_OFFLINE,
                message="Target device is offline or disconnected.",
                suggested_action="retry",
                retry_allowed=True,
                backoff_seconds=3.0,
                details={"tool": tool_name},
            )

        if "timeout" in err or "timed out" in err or "connection refused" in err or "econnrefused" in err or "network" in err:
            return FailureAnalysis(
                category=FailureCategory.NETWORK_FAILURE,
                message="Network error or connection timeout during action.",
                suggested_action="retry",
                retry_allowed=True,
                backoff_seconds=2.0,
                details={"tool": tool_name},
            )

        # 4. Element / UI target not found
        if "element not found" in err or "selector not found" in err or "unable to locate" in err or "no matching control" in err:
            return FailureAnalysis(
                category=FailureCategory.ELEMENT_NOT_FOUND,
                message="Target UI element was not found in active DOM or Accessibility tree.",
                suggested_action="fallback",  # Re-observe -> Accessibility -> Vision
                retry_allowed=True,
                backoff_seconds=1.0,
                details={"strategy": "re-observe-with-vision"},
            )

        # 5. App crashed / missing
        if "app not installed" in err or "package not found" in err or "cannot find application" in err:
            return FailureAnalysis(
                category=FailureCategory.APP_NOT_INSTALLED,
                message="Required application is not installed on the target device.",
                suggested_action="replan",
                retry_allowed=False,
                backoff_seconds=0.0,
                details={"tool": tool_name},
            )

        if "crashed" in err or "not responding" in err or "killed" in err:
            return FailureAnalysis(
                category=FailureCategory.APP_CRASHED,
                message="Application process crashed or became unresponsive.",
                suggested_action="retry",
                retry_allowed=True,
                backoff_seconds=2.0,
                details={"tool": tool_name},
            )

        # Default / Unknown
        return FailureAnalysis(
            category=FailureCategory.UNKNOWN_FAILURE,
            message=error_text or "Unspecified tool execution failure.",
            suggested_action="replan",
            retry_allowed=True,
            backoff_seconds=1.0,
            details={"raw_error": error_text},
        )

    def check_loop_or_stuck(self, tool_name: str, params_str: str) -> bool:
        """Returns True if the agent is stuck in an infinite repetitive call loop."""
        import hashlib
        call_hash = hashlib.sha256(f"{tool_name}:{params_str}".encode("utf-8")).hexdigest()
        now = time.time()
        self._action_call_history.append((tool_name, call_hash, now))

        # Inspect last N calls
        recent = [h for t, h, ts in self._action_call_history[-self.max_consecutive_duplicates:]]
        if len(recent) >= self.max_consecutive_duplicates and len(set(recent)) == 1:
            logger.error("🛑 RecoveryEngine: Infinite tool loop detected on '%s'!", tool_name)
            return True
        return False

    def compute_backoff(self, attempt: int, base_seconds: float = 1.0, max_seconds: float = 30.0) -> float:
        """Calculate exponential backoff with ceiling."""
        delay = min(max_seconds, base_seconds * (2 ** (attempt - 1)))
        return delay


_recovery_engine_instance: Optional[RecoveryEngine] = None


def get_recovery_engine() -> RecoveryEngine:
    global _recovery_engine_instance
    if _recovery_engine_instance is None:
        _recovery_engine_instance = RecoveryEngine()
    return _recovery_engine_instance
