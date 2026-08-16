#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brjarvis.py - BRJARVIS Global Unified Command Line Tool & Entry Point Shim
==========================================================================
This file is the project-root shim that allows `python brjarvis.py` and
`import brjarvis` from the project root to resolve to the real package
at src/brjarvis/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Path Setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
_PKG_DIR = _SRC / "brjarvis"

# Ensure src/ is on sys.path so `import brjarvis` resolves to src/brjarvis/
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Make root shim act as the package namespace if imported as 'brjarvis'
__path__ = [str(_PKG_DIR)]

# ── Canonical Python Enforcement ──────────────────────────────────────────────
from brjarvis.core.paths import ensure_canonical_python  # noqa: E402
ensure_canonical_python()

# ── Eager Imports for Legacy Namespace Registration ───────────────────────────
# Eagerly import brjarvis (triggers LegacyNamespaceFinder installation in src/brjarvis/__init__.py)
try:
    import brjarvis as _brjarvis_pkg  # noqa: F401
except Exception:
    pass

# Eagerly register redteam alias so legacy `import redteam` works everywhere
try:
    import brjarvis.guardian.redteam  # noqa: F401 - triggers sys.modules["redteam"] aliasing
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


if __name__ == "__main__":
    sys.exit(main())
