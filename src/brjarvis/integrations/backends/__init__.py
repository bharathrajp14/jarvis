# backends/__init__.py — JARVIS MK37 Backend Package
"""
Unified AI backend package. Auto-discovers and exports all backend classes.
All optional backends are guarded with try/except to prevent import crashes
when their underlying SDK packages aren't installed.
"""
from __future__ import annotations

import sys
_mod = sys.modules.get(__name__)
if _mod:
    sys.modules["backends"] = _mod
    sys.modules["brjarvis.integrations.backends"] = _mod

from .base import BaseBackend
from .gemini import GeminiBackend

# Optional backends — gracefully skip if SDK not installed
try:
    from .openai_compat import OpenAIBackend
except ImportError:
    OpenAIBackend = None  # type: ignore[assignment, misc]

try:
    from .anthropic import ClaudeBackend
except ImportError:
    ClaudeBackend = None  # type: ignore[assignment, misc]

try:
    from .deepseek import DeepSeekBackend
except ImportError:
    DeepSeekBackend = None  # type: ignore[assignment, misc]

try:
    from .ollama import OllamaBackend
except ImportError:
    OllamaBackend = None  # type: ignore[assignment, misc]

try:
    from .nvidia import NvidiaBackend
except ImportError:
    NvidiaBackend = None  # type: ignore[assignment, misc]

try:
    from .mistral import MistralBackend
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
