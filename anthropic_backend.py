# anthropic_backend.py — Root Backward-Compatibility Shim
from backends.anthropic import ClaudeBackend

# Alias for legacy callers expecting AnthropicBackend
AnthropicBackend = ClaudeBackend

__all__ = ["ClaudeBackend", "AnthropicBackend"]
