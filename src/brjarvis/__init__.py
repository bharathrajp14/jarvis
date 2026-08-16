# src/brjarvis/__init__.py — Master Package for BR JARVIS Cognitive Multi-Modal OS
"""
BR JARVIS MK40.2+ (Jarvis)
Autonomous Cognitive Agent Architecture & Isolated Sandbox Lifecycle Engine
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Dynamic Path & Namespace Compatibility Injection ────────────────────────
_PACKAGE_DIR = Path(__file__).resolve().parent
_SRC_DIR = _PACKAGE_DIR.parent
_PROJECT_ROOT = _SRC_DIR.parent

for _p in [str(_PACKAGE_DIR), str(_SRC_DIR), str(_PROJECT_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Aliasing legacy top-level namespace names to brjarvis.*
_ALIASES = {
    "core": "brjarvis.core",
    "career": "brjarvis.career",
    "agent": "brjarvis.agent",
    "memory": "brjarvis.memory",
    "tools": "brjarvis.tools",
    "actions": "brjarvis.actions",
    "connectors": "brjarvis.connectors",
    "voice": "brjarvis.voice",
    "vision": "brjarvis.vision",
    "ui": "brjarvis.ui",
    "desktop_ui": "brjarvis.desktop",
    "skills": "brjarvis.skills",
    "orchestrator": "brjarvis.orchestrator",
    "router": "brjarvis.router",
    "gateway": "brjarvis.gateway",
    "guardian": "brjarvis.guardian",
    "security": "brjarvis.security",
    "workflow": "brjarvis.workflow",
    "backends": "brjarvis.integrations.backends",
    "native": "brjarvis.native",
    "context": "brjarvis.context",
    "events": "brjarvis.events",
    "history": "brjarvis.history",
    "computer": "brjarvis.computer",
    "mobile": "brjarvis.integrations.mobile",
    "reasoning": "brjarvis.reasoning",
    "redteam": "brjarvis.guardian.redteam",
    "evolution": "brjarvis.evolution",
    "plugins": "brjarvis.plugins",
    "screen_server": "brjarvis.screen_server",
    "multi_agent": "brjarvis.multi_agent",
}

import importlib.abc
import importlib.util

class LegacyNamespaceFinder(importlib.abc.MetaPathFinder):
    """Universal transparent import router for legacy package paths to brjarvis.*"""
    def find_spec(self, fullname: str, path=None, target=None):
        for legacy, canonical in _ALIASES.items():
            if fullname == legacy:
                try:
                    spec = importlib.util.find_spec(canonical)
                    if spec is not None:
                        mod = importlib.import_module(canonical)
                        sys.modules[legacy] = mod
                    return spec
                except Exception:
                    pass
            elif fullname.startswith(legacy + "."):
                rel = fullname[len(legacy):]
                target_name = canonical + rel
                try:
                    if legacy not in sys.modules:
                        try:
                            sys.modules[legacy] = importlib.import_module(canonical)
                        except Exception:
                            pass
                    mod = importlib.import_module(target_name)
                    sys.modules[fullname] = mod
                    return getattr(mod, "__spec__", None)
                except Exception:
                    pass
        return None

if not any(isinstance(f, LegacyNamespaceFinder) for f in getattr(sys, "meta_path", [])):
    sys.meta_path.insert(0, LegacyNamespaceFinder())

try:
    from brjarvis.core.version import VERSION, BUILD, CODENAME
    __version__ = VERSION
    __build__ = BUILD
    __codename__ = CODENAME
except Exception:
    __version__ = "40.2.0"
    __build__ = "2026.08.16"
    __codename__ = "MK40.2-PRODUCTION"

from brjarvis.core.paths import get_path_manager, PathManager, paths

# Eagerly import aliased packages to trigger self-registration in sys.modules
try:
    import brjarvis.guardian.redteam as _redteam  # noqa: F401
except Exception:
    pass

__all__ = [
    "__version__",
    "__build__",
    "__codename__",
    "get_path_manager",
    "PathManager",
    "paths",
]
