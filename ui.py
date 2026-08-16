# ui.py — Root-level shim for the JARVIS UI package
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
_UI_DIR = _SRC / "brjarvis" / "ui"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_UI_DIR) not in sys.path:
    sys.path.insert(0, str(_UI_DIR))

from brjarvis.core.paths import ensure_canonical_python
ensure_canonical_python()

__path__ = [str(_UI_DIR)]

def __getattr__(name: str):
    import brjarvis.ui as _ui
    return getattr(_ui, name)

if __name__ == "__main__":
    from brjarvis.apps.desktop import main
    sys.exit(main())
