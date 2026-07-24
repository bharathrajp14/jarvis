# gemini_backend.py — Root Backward-Compatibility Shim
from backends.gemini import GeminiBackend

# Alias for legacy callers expecting GeminiBackendWrapper
GeminiBackendWrapper = GeminiBackend

__all__ = ["GeminiBackend", "GeminiBackendWrapper"]
