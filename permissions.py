"""permissions.py — Backward-compatible shim for BR JARVIS Security Engine"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from brjarvis.security.permissions import (
    _normalize_mode,
    PermissionMode,
    PermissionPolicy,
    DESTRUCTIVE_TOOLS,
    PERMISSIONS,
    ALWAYS_ALLOWED,
    ALWAYS_CONFIRM,
    _build_global_policy,
    _load_scope_defaults,
    evaluate_action_policy,
)

def __getattr__(name: str):
    import brjarvis.security.permissions as _p
    return getattr(_p, name)
