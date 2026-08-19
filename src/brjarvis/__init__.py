# src/brjarvis/__init__.py — Master Package for BR JARVIS Cognitive Multi-Modal OS
"""
BR JARVIS v41.0 (MARK XLI)
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

for _p in [str(_SRC_DIR), str(_PROJECT_ROOT)]:
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
    "contracts": "brjarvis.contracts",
}

import importlib.abc
import importlib.util


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, canonical_name: str):
        self.canonical_name = canonical_name

    def create_module(self, spec):
        mod = importlib.import_module(self.canonical_name)
        sys.modules[spec.name] = mod
        return mod

    def exec_module(self, module):
        pass


class LegacyNamespaceFinder(importlib.abc.MetaPathFinder):
    """Universal transparent import router for legacy package paths to brjarvis.*"""

    def find_spec(self, fullname: str, path=None, target=None):
        for legacy, canonical in _ALIASES.items():
            if fullname == legacy:
                try:
                    canonical_spec = importlib.util.find_spec(canonical)
                    if canonical_spec is None:
                        return None
                    spec = importlib.util.spec_from_loader(
                        fullname,
                        _AliasLoader(canonical),
                        is_package=bool(canonical_spec.submodule_search_locations),
                    )
                    if spec is not None and canonical_spec.submodule_search_locations:
                        spec.submodule_search_locations = list(canonical_spec.submodule_search_locations)
                    return spec
                except Exception:
                    pass
            elif fullname.startswith(legacy + "."):
                rel = fullname[len(legacy) :]
                canonical_sub = canonical + rel
                try:
                    canonical_spec = importlib.util.find_spec(canonical_sub)
                    if canonical_spec is None:
                        return None
                    spec = importlib.util.spec_from_loader(
                        fullname,
                        _AliasLoader(canonical_sub),
                        is_package=bool(canonical_spec.submodule_search_locations),
                    )
                    if spec is not None and canonical_spec.submodule_search_locations:
                        spec.submodule_search_locations = list(canonical_spec.submodule_search_locations)
                    return spec
                except Exception:
                    pass
        return None


if not any(isinstance(f, LegacyNamespaceFinder) for f in getattr(sys, "meta_path", [])):
    sys.meta_path.insert(0, LegacyNamespaceFinder())

try:
    from brjarvis.core.version import BUILD, CODENAME, VERSION

    __version__ = VERSION
    __build__ = BUILD
    __codename__ = CODENAME
except Exception:
    __version__ = "41.0.0"
    __build__ = "2026-08-18"
    __codename__ = "MARK XLI"

from brjarvis.core.paths import PathManager, get_path_manager, paths

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
