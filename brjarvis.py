#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brjarvis.py - BRJARVIS Global Unified Command Line Tool & Entry Point Shim
==========================================================================
This file is the project-root shim. When Python finds 'brjarvis.py' in the
project root (because '.' is on sys.path), this runs instead of
src/brjarvis/__init__.py. We must therefore replicate any critical bootstrap
logic that __init__.py provides.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ── Path Setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
_PKG_DIR = _SRC / "brjarvis"

for _p in [str(_SRC), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Make root shim act as the package namespace when imported as 'brjarvis'
__path__ = [str(_PKG_DIR)]

# ── Canonical Python Enforcement ──────────────────────────────────────────────
from brjarvis.core.paths import ensure_canonical_python  # noqa: E402
ensure_canonical_python()

# ── Legacy Namespace Aliases ──────────────────────────────────────────────────
# Install a meta-path finder so that bare `import memory`, `import tools` etc.
# transparently resolve to brjarvis.memory, brjarvis.tools etc.
# This replicates the LegacyNamespaceFinder defined in src/brjarvis/__init__.py,
# which cannot be auto-loaded here because this shim file IS 'brjarvis.py'.
import importlib as _il
import importlib.abc as _abc
import importlib.util as _ilu

_LEGACY_ALIASES = {
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
    "reasoning": "brjarvis.reasoning",
    "redteam": "brjarvis.guardian.redteam",
    "evolution": "brjarvis.evolution",
    "plugins": "brjarvis.plugins",
    "multi_agent": "brjarvis.multi_agent",
}


class _ShimAliasLoader(_abc.Loader):
    def __init__(self, canonical_name: str):
        self.canonical_name = canonical_name

    def create_module(self, spec):
        mod = _il.import_module(self.canonical_name)
        sys.modules[spec.name] = mod
        return mod

    def exec_module(self, module):
        pass


class _ShimLegacyFinder(_abc.MetaPathFinder):
    """Transparent import router: bare legacy names -> brjarvis.* canonical paths."""
    def find_spec(self, fullname: str, path=None, target=None):
        for legacy, canonical in _LEGACY_ALIASES.items():
            if fullname == legacy:
                try:
                    canonical_spec = _ilu.find_spec(canonical)
                    if canonical_spec is None:
                        return None
                    spec = _ilu.spec_from_loader(
                        fullname,
                        _ShimAliasLoader(canonical),
                        is_package=bool(canonical_spec.submodule_search_locations),
                    )
                    if spec is not None and canonical_spec.submodule_search_locations:
                        spec.submodule_search_locations = list(canonical_spec.submodule_search_locations)
                    return spec
                except Exception:
                    pass
            elif fullname.startswith(legacy + "."):
                suffix = fullname[len(legacy):]
                canonical_sub = canonical + suffix
                try:
                    canonical_spec = _ilu.find_spec(canonical_sub)
                    if canonical_spec is None:
                        return None
                    spec = _ilu.spec_from_loader(
                        fullname,
                        _ShimAliasLoader(canonical_sub),
                        is_package=bool(canonical_spec.submodule_search_locations),
                    )
                    if spec is not None and canonical_spec.submodule_search_locations:
                        spec.submodule_search_locations = list(canonical_spec.submodule_search_locations)
                    return spec
                except Exception:
                    pass
        return None


if not any(isinstance(f, _ShimLegacyFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _ShimLegacyFinder())

# ── Eager redteam alias ───────────────────────────────────────────────────────
try:
    import brjarvis.guardian.redteam  # noqa: F401
except Exception:
    pass

# ── Package Metadata ──────────────────────────────────────────────────────────
try:
    from brjarvis.core.version import VERSION, BUILD, CODENAME
    __version__ = VERSION
    __build__ = BUILD
    __codename__ = CODENAME
except Exception:
    __version__ = "40.2.0"
    __build__ = "2026.08.16"
    __codename__ = "MK40.2-PRODUCTION"


def main() -> int:
    from brjarvis.apps.cli import main as cli_main
    return cli_main()


def __getattr__(name: str):
    try:
        mod = _il.import_module(f"brjarvis.{name}")
        globals()[name] = mod
        return mod
    except Exception:
        raise AttributeError(f"module 'brjarvis' has no attribute '{name}'")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\n\n[JARVIS] Session terminated by user. Goodbye.")
        sys.exit(0)
    except SystemExit as _se:
        sys.exit(_se.code if _se.code is not None else 0)
    except Exception as _fatal:
        print(f"\n[Fatal Error] {_fatal}", file=sys.stderr)
        sys.exit(1)

