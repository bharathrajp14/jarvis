#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apps/desktop/main.py — Desktop GUI Application Entry Point"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from brjarvis.apps.desktop import main

if __name__ == "__main__":
    sys.exit(main())
