"""
ui.py — Root-level shim for the JARVIS UI package.

This file exists at the project root so that code doing:
    from ui import JarvisUI
or
    from ui.app import JarvisUI
both work correctly.

The actual implementation lives in the ui/ package (ui/app.py).
The canonical launcher entry point is ui_mark.py::run_voice_ui().
"""
from ui.app import (  # noqa: F401
    JarvisUI,
    HeadlessJarvisUI,
    is_gui_available,
    _RootShim,
)
