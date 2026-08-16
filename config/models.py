# config/models.py — Shim to brjarvis.config.models
from __future__ import annotations
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from brjarvis.config.models import *  # noqa: F401,F403
