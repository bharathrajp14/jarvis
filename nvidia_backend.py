# nvidia_backend.py — Root Backward-Compatibility Shim
from backends.nvidia import NvidiaBackend

# Alias for legacy callers expecting NVIDIABackend
NVIDIABackend = NvidiaBackend

__all__ = ["NvidiaBackend", "NVIDIABackend"]
