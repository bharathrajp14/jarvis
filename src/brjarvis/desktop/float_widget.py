#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BR JARVIS floating-widget compatibility entry point.

Presentation lives in ``floating_surface.py``. Runtime behavior lives in
``floating_runtime.py``. This module preserves the historical public names and
launcher contract while keeping the implementation boundaries explicit.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Any, Optional

from brjarvis.desktop.floating_runtime import FloatingRuntimeAdapter, FloatingWidgetState
from brjarvis.desktop.floating_surface import HAS_QT, JarvisFloat

logger = logging.getLogger(__name__)


class HeadlessFloat:
    """Headless command projection with the same runtime contract as the dock."""

    def __init__(self, orchestrator: Any = None, voice_trigger: Any = None) -> None:
        self._runtime = FloatingRuntimeAdapter(orchestrator=orchestrator, voice_trigger=voice_trigger)
        self._runtime.update(capabilities={"graphical_display": False, "tray": False})
        self._runtime_unsubscribe = self._runtime.subscribe(self._print_state)

    def _print_state(self, state: FloatingWidgetState) -> None:
        print(f"[FLOAT] {state.assistant.upper()} · {state.message}")
        if state.error:
            print(f"[FLOAT ERROR] {state.error}", file=sys.stderr)

    def write_log(self, text: str) -> None:
        self._runtime.update(message=str(text))

    def set_state(self, state: str) -> None:
        self._runtime.set_assistant_state(state)

    def set_runtime(self, runtime: str) -> None:
        self._runtime.set_runtime(runtime)

    def submit_command(self, text: str) -> None:
        self._runtime.submit_command(text)

    def trigger_voice(self) -> None:
        self._runtime.trigger_voice()

    def refresh_connectors(self) -> None:
        self._runtime.refresh_connectors()

    @property
    def state(self) -> FloatingWidgetState:
        return self._runtime.snapshot()

    @property
    def speaking(self) -> bool:
        return self._runtime.snapshot().audio == "playing"

    @speaking.setter
    def speaking(self, value: bool) -> None:
        self._runtime.set_audio_state("playing" if value else "inactive")

    @property
    def muted(self) -> bool:
        return self._runtime.snapshot().audio == "muted"

    @muted.setter
    def muted(self, value: bool) -> None:
        self._runtime.set_audio_state("muted" if value else "inactive")


def create_float_widget(orchestrator: Any = None, voice_trigger: Any = None):
    """Create the Qt dock when available, otherwise return the headless projection."""
    if not HAS_QT or JarvisFloat is None:
        return HeadlessFloat(orchestrator=orchestrator, voice_trigger=voice_trigger)
    try:
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 10))
        widget = JarvisFloat(orchestrator=orchestrator, voice_trigger=voice_trigger)
        widget.show()
        return widget
    except Exception as exc:  # noqa: BLE001 - compatibility fallback boundary
        logger.warning("Floating dock Qt initialization failed: %s", exc)
        return HeadlessFloat(orchestrator=orchestrator, voice_trigger=voice_trigger)


def main(argv: Optional[list[str]] = None) -> int:
    """Launch the redesigned Orb + Command Rail surface."""
    if not HAS_QT or JarvisFloat is None:
        logger.warning("PySide6 is unavailable; graphical floating dock cannot start.")
        print("BR JARVIS floating dock requires PySide6 for graphical mode.", file=sys.stderr)
        return 1

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setFont(QFont("Segoe UI", 10))
    app.setQuitOnLastWindowClosed(False)
    widget = JarvisFloat()
    widget.set_runtime("starting")
    widget.show_orb()

    def _bootstrap_runtime() -> None:
        try:
            from brjarvis.core.bootstrap import build_assistant_runtime

            runtime = build_assistant_runtime()
            widget._runtime.attach_runtime(orchestrator=runtime.orchestrator)
        except Exception as exc:  # noqa: BLE001 - startup boundary becomes visible runtime state
            logger.info("Floating dock runtime unavailable: %s", exc)
            widget._runtime.update(runtime="error", error="Runtime unavailable. Open the workspace or retry.")

    threading.Thread(target=_bootstrap_runtime, daemon=True, name="floating-runtime-bootstrap").start()
    return app.exec()


__all__ = [
    "FloatingRuntimeAdapter",
    "FloatingWidgetState",
    "HeadlessFloat",
    "JarvisFloat",
    "create_float_widget",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
