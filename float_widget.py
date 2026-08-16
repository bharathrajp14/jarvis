#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""float_widget.py — BR JARVIS Floating HUD Widget Shim"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from brjarvis.desktop.float_widget import *
except Exception:
    pass

if __name__ == "__main__":
    from brjarvis.apps.desktop import main
    sys.exit(main())
