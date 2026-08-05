# ui/_qt.py — Canonical Qt Import Shim for JARVIS UI
# =====================================================
# Single source-of-truth for all Qt imports used by the ui/ package.
# Every ui/ module imports from here instead of repeating 30 lines of
# PySide6/PyQt6 boilerplate.
#
# Usage in other ui/ modules:
#     from ui._qt import (
#         _USE_PYSIDE6, _WIN_HIDE,
#         QApplication, QMainWindow, QWidget, ...
#     )
from __future__ import annotations

import os
import platform
import subprocess
import sys

# ── Platform-specific subprocess flag ────────────────────────────────────────
if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}

# ── Qt backend detection (PySide6 preferred, PyQt6 fallback) ─────────────────
_USE_PYSIDE6 = False
try:
    import PySide6  # type: ignore[import-not-found]  # noqa: F401
    _USE_PYSIDE6 = True
except ImportError:
    try:
        import PyQt6  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        pass  # Headless mode — GUI not available

# ── Qt Imports ────────────────────────────────────────────────────────────────
if _USE_PYSIDE6:
    from PySide6.QtCore import (  # type: ignore[import-not-found]
        QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
        QTimer, QUrl, Signal as pyqtSignal,
    )
    from PySide6.QtGui import (  # type: ignore[import-not-found]
        QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent, QFont,
        QFontDatabase, QKeySequence, QLinearGradient, QPainter, QPainterPath,
        QPen, QPixmap, QRadialGradient, QShortcut,
    )
    from PySide6.QtWidgets import (  # type: ignore[import-not-found]
        QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
        QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSplitter,
        QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
    )
else:
    from PyQt6.QtCore import (  # type: ignore[import-not-found]
        QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
        QTimer, QUrl, pyqtSignal,
    )
    from PyQt6.QtGui import (  # type: ignore[import-not-found]
        QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent, QFont,
        QFontDatabase, QKeySequence, QLinearGradient, QPainter, QPainterPath,
        QPen, QPixmap, QRadialGradient, QShortcut,
    )
    from PyQt6.QtWidgets import (  # type: ignore[import-not-found]
        QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
        QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSplitter,
        QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
    )

__all__ = [
    "_USE_PYSIDE6", "_WIN_HIDE",
    # Core
    "QEasingCurve", "QMimeData", "QObject", "QPointF", "QRectF", "QSize",
    "Qt", "QTimer", "QUrl", "pyqtSignal",
    # Gui
    "QBrush", "QColor", "QConicalGradient", "QDragEnterEvent", "QDropEvent",
    "QFont", "QFontDatabase", "QKeySequence", "QLinearGradient", "QPainter",
    "QPainterPath", "QPen", "QPixmap", "QRadialGradient", "QShortcut",
    # Widgets
    "QApplication", "QFileDialog", "QFrame", "QHBoxLayout", "QLabel",
    "QLineEdit", "QMainWindow", "QPushButton", "QScrollArea", "QSizePolicy",
    "QSplitter", "QStackedWidget", "QTextEdit", "QVBoxLayout", "QWidget",
    "QProgressBar",
]
