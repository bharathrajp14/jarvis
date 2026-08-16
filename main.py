#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main.py — Canonical Legacy Backward-Compatible Entrypoint"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from brjarvis.core.paths import ensure_canonical_python
ensure_canonical_python()

from brjarvis.apps.bootstrap import main

if __name__ == "__main__":
    sys.exit(main())
