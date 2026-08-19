# core/errors.py — Canonical Typed Error Hierarchy for BR JARVIS
"""
Typed error classification system for BR JARVIS.
Every error includes an optional trace_id and user_friendly_message,
guaranteeing transparent debugging for developers and clear non-technical
explanations for users.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional


class JarvisError(Exception):
    """Base exception for all BR JARVIS runtime errors."""

    def __init__(
        self,
        message: str,
        *,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.task_id = task_id or ""
        self.user_message = user_message or message
        self.details = details or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "user_message": self.user_message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ConfigurationError(JarvisError):
    """Raised when environment variables, config files, or settings are invalid."""

    pass


class ProviderError(JarvisError):
    """Raised when an AI model provider backend encounters an error."""

    pass


class ProviderTimeout(ProviderError):
    """Raised when a model completion request exceeds its allotted timeout."""

    pass


class ProviderRateLimit(ProviderError):
    """Raised when a provider rejects requests due to rate or quota limits."""

    pass


class ToolError(JarvisError):
    """Raised when a registered tool fails during execution."""

    pass


class ToolTimeout(ToolError):
    """Raised when a tool execution exceeds its timeout limit."""

    pass


class SecurityPolicyError(JarvisError):
    """Raised when an action violates security, permission, or path policy."""

    pass


PermissionPolicyError = SecurityPolicyError


class VerificationError(JarvisError):
    """Raised when an action postcondition verification check fails."""

    pass


class ArtifactError(JarvisError):
    """Raised when artifact creation, export, or sandbox handoff fails."""

    pass


class VisionError(JarvisError):
    """Raised when screen capture, OCR, DOM bridge, or VLM analysis fails."""

    pass


class STTError(JarvisError):
    """Raised when audio capture or speech-to-text recognition fails."""

    pass


class TTSError(JarvisError):
    """Raised when text-to-speech synthesis fails."""

    pass


class MemoryError(JarvisError):
    """Raised when persistent memory storage, retrieval, or embedding fails."""

    pass


class WorkflowError(JarvisError):
    """Raised when DAG scheduling, stage decomposition, or recovery fails."""

    pass


class CancellationError(JarvisError):
    """Raised when a task or workflow is cancelled by user or timeout."""

    pass
