#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui_mark.py — BR JARVIS Cyberpunk HUD Entry Point Shim"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from brjarvis.apps.desktop import main
import brjarvis.desktop.ui_mark as _um
def _is_jarvis_running(port: int = 8000) -> bool:
    return _um._is_jarvis_running(port)

def _port_free(port: int) -> bool:
    return _um._port_free(port)

def _find_available_jarvis_port(preferred_port: int = 8000) -> int:
    if _is_jarvis_running(preferred_port) or _port_free(preferred_port):
        return preferred_port
    for p in (8080, 8088, 8888, 5000, 8001, 8002):
        if _is_jarvis_running(p) or _port_free(p):
            return p
    return preferred_port

def _server_port() -> int:
    return _um._server_port()

def _generate_remote_credentials() -> tuple[str, str]:
    return _um._generate_remote_credentials()

def __getattr__(name: str):
    return getattr(_um, name)

def __setattr__(name: str, value):
    super().__setattr__(name, value)
    try:
        setattr(_um, name, value)
    except Exception:
        pass

if __name__ == "__main__":
    sys.exit(main())
