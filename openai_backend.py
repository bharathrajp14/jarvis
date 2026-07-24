# openai_backend.py — Root Backward-Compatibility Shim
from backends.openai_compat import OpenAIBackend

# Alias for legacy callers expecting OpenAICompatBackend
OpenAICompatBackend = OpenAIBackend

__all__ = ["OpenAIBackend", "OpenAICompatBackend"]
