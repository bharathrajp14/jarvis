# src/brjarvis/apps/__init__.py
from __future__ import annotations

from brjarvis.apps.bootstrap import main as bootstrap_main
from brjarvis.apps.cli import main as cli_main
from brjarvis.apps.web import main as web_main
from brjarvis.apps.desktop import main as desktop_main
from brjarvis.apps.voice import main as voice_main

__all__ = [
    "bootstrap_main",
    "cli_main",
    "web_main",
    "desktop_main",
    "voice_main",
]
