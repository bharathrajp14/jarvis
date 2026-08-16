#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start.py — BR JARVIS MK40.2+ Canonical Application Bootstrap & Launcher Shim
=============================================================================
Unified launcher providing full backwards compatibility for:
  python start.py
  python start.py cli
  python start.py web
  python start.py doctor
  python start.py voice
  python start.py status
  python start.py career
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src to sys.path
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from brjarvis.core.paths import ensure_canonical_python
ensure_canonical_python()

import brjarvis
from brjarvis.apps.bootstrap import (
    main,
    launch_cli,
    launch_web_server,
    launch_voice,
    show_status,
)
from brjarvis.diagnostics.doctor import run_diagnostics_audit


def doctor(auto_confirm: bool = False):
    """Backwards-compatible doctor entry point."""
    return run_diagnostics_audit(auto_repair=auto_confirm)


def launch_career_studio():
    """Launch the Career OS Studio web interface."""
    launch_web_server(open_url="http://127.0.0.1:8000/career")


def launch_career_sync():
    """Trigger career application and email inbox synchronization."""
    from brjarvis.career.crm.database import get_career_crm_db
    db = get_career_crm_db()
    return db.get_stats()


if __name__ == "__main__":
    sys.exit(main())
