# backends/__init__.py — JARVIS MK37 Backend Package
"""
Unified AI backend package. Auto-discovers and exports all backend classes.
All optional backends are guarded with try/except to prevent import crashes
when their underlying SDK packages aren't installed.
"""
from __future__ import annotations

from backends.base import BaseBackend
from backends.gemini import GeminiBackend

# Optional backends — gracefully skip if SDK not installed
try:
    from backends.openai_compat import OpenAIBackend
except ImportError:
    OpenAIBackend = None  # type: ignore[assignment, misc]

try:
    from backends.anthropic import ClaudeBackend
except ImportError:
    ClaudeBackend = None  # type: ignore[assignment, misc]

try:
    from backends.deepseek import DeepSeekBackend
except ImportError:
    DeepSeekBackend = None  # type: ignore[assignment, misc]

try:
    from backends.ollama import OllamaBackend
except ImportError:
    OllamaBackend = None  # type: ignore[assignment, misc]

try:
    from backends.nvidia import NvidiaBackend
except ImportError:
    NvidiaBackend = None  # type: ignore[assignment, misc]

try:
    from backends.mistral import MistralBackend
except ImportError:
    MistralBackend = None  # type: ignore[assignment, misc]

__all__ = [
    "BaseBackend",
    "GeminiBackend",
    "OpenAIBackend",
    "ClaudeBackend",
    "DeepSeekBackend",
    "OllamaBackend",
    "NvidiaBackend",
    "MistralBackend",
]
