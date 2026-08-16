#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
float_widget.py -- BR JARVIS MK38 Floating HUD Widget
A compact, always-on-top glassmorphism JARVIS panel.

Features:
  - Glassmorphism dark panel with frosted effect
  - 5-bar animated waveform (pulses during speech/TTS)
  - Live status ring (cyan=listening, orange=thinking, green=speaking, red=error)
  - Real-time log (last 8 messages)
  - Connector badges (live hub status)
  - Voice input field + mic button
  - Draggable by click-dragging anywhere
  - Minimizable to 64x64 tray bubble (double-click or Esc)
  - Alt+Space global hotkey to toggle show/hide
  - Tray icon with right-click context menu

Usage:
    python float_widget.py               # standalone float only
    python float_widget.py --with-jarvis # also launches JARVIS backend
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from ui import setup_qt_paths
    setup_qt_paths()
except Exception:
    pass

try:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect,
        QSizePolicy, QSystemTrayIcon, QMenu,
    )
    from PySide6.QtCore import Qt, QTimer, QPoint, QSize, Signal, Slot
    from PySide6.QtGui import (
        QColor, QPainter, QPen, QBrush, QLinearGradient,
        QFont, QIcon, QPixmap, QKeySequence, QShortcut, QPainterPath,
    )
    _HAS_QT = True
except ImportError:
    _HAS_QT = False

logger = logging.getLogger(__name__)

C = {}
if _HAS_QT:
    C = {
        "bg_deep":       QColor(6, 8, 16),
        "bg_panel":      QColor(10, 13, 24, 218),
        "accent_cyan":   QColor(0, 210, 255),
        "accent_orange": QColor(255, 140, 0),
        "accent_green":  QColor(0, 220, 130),
        "accent_red":    QColor(255, 60, 60),
        "accent_purple": QColor(130, 50, 220),
        "text_primary":  QColor(230, 240, 255),
        "text_muted":    QColor(90, 110, 140),
        "border":        QColor(40, 55, 80, 160),
    }

_STATE_COLORS = {
    "LISTENING":  "accent_cyan",
    "THINKING":   "accent_orange",
    "SPEAKING":   "accent_green",
    "EXECUTING":  "accent_purple",
    "ERROR":      "accent_red",
    "IDLE":       "text_muted",
}


def _btn_style(danger=False, accent=False):
    if danger:
        return ("QPushButton{background:rgba(255,60,60,.10);color:#ff6060;"
                "border:1px solid rgba(255,60,60,.25);border-radius:6px;font-size:11px;font-weight:600;}"
                "QPushButton:hover{background:rgba(255,60,60,.25);}")
    if accent:
        return ("QPushButton{background:rgba(0,210,255,.12);color:#00d2ff;"
                "border:1px solid rgba(0,210,255,.30);border-radius:8px;font-size:14px;}"
                "QPushButton:hover{background:rgba(0,210,255,.22);}")
    return ("QPushButton{background:rgba(255,255,255,.06);color:#8899bb;"
            "border:1px solid rgba(255,255,255,.10);border-radius:6px;font-size:11px;}"
            "QPushButton:hover{background:rgba(255,255,255,.12);color:#c0d0e8;}")


if _HAS_QT:
    class WaveformWidget(QWidget):
        """5-bar animated equalizer waveform."""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setFixedSize(64, 32)
            self._bars = [0.15, 0.35, 0.60, 0.35, 0.15]
            self._targets = list(self._bars)
            self._active = False
            self._color = C["accent_cyan"]
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._animate)
            self._timer.start(60)

        def set_active(self, active, color=None):
            self._active = active
            if color:
                self._color = color
            import random
            if active:
                self._targets = [random.uniform(0.3, 1.0) for _ in range(5)]
            else:
                self._targets = [0.08, 0.15, 0.20, 0.15, 0.08]

        def _animate(self):
            import random
            if self._active:
                self._targets = [random.uniform(0.25, 1.0) for _ in range(5)]
            for i in range(5):
                diff = self._targets[i] - self._bars[i]
                if abs(diff) > 0.01:
                    self._bars[i] += diff * 0.35
            self.update()

        def paintEvent(self, event):
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            w, h = self.width(), self.height()
            bar_w = max(4, (w - 4 * 3) // 5)
            x = 0
            for ratio in self._bars:
                bar_h = max(3, int(ratio * (h - 4)))
                y = h - bar_h - 2
                grad = QLinearGradient(0, y, 0, y + bar_h)
                col = QColor(self._color); col.setAlpha(200)
                grad.setColorAt(0.0, col)
                bot = QColor(self._color); bot.setAlpha(55)
                grad.setColorAt(1.0, bot)
                p.setBrush(QBrush(grad)); p.setPen(Qt.NoPen)
                p.drawRoundedRect(x, y, bar_w, bar_h, 2, 2)
                x += bar_w + 3
            p.end()


    class StatusRingWidget(QWidget):
        """Animated pulsing status circle."""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setFixedSize(18, 18)
            self._state = "IDLE"
            self._pulse = 0.0
            self._direction = 1
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(40)


        def set_state(self, state):
            self._state = state.upper(); self.update()

        def _tick(self):
            self._pulse += 0.05 * self._direction
            if self._pulse >= 1.0: self._direction = -1
            elif self._pulse <= 0.0: self._direction = 1
            self.update()

        def paintEvent(self, event):
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            ck = _STATE_COLORS.get(self._state, "text_muted")
            color = QColor(C.get(ck, C["text_muted"]))
            glow = QColor(color); glow.setAlpha(int(40 + 80 * self._pulse))
            p.setPen(Qt.NoPen); p.setBrush(QBrush(glow))
            p.drawEllipse(1, 1, 16, 16)
            inner = QColor(color); inner.setAlpha(220)
            p.setBrush(QBrush(inner)); p.drawEllipse(4, 4, 10, 10)
            p.end()


    class GlassPanel(QFrame):
        """Frosted glass background panel."""
        def paintEvent(self, event):
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            rect = self.rect()
            grad = QLinearGradient(0, 0, 0, rect.height())
            grad.setColorAt(0.0, QColor(12, 16, 30, 215))
            grad.setColorAt(1.0, QColor(6, 9, 20, 225))
            path = QPainterPath()
            path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 14, 14)
            p.fillPath(path, QBrush(grad))
            border_pen = QPen(QColor(0, 210, 255, 45)); border_pen.setWidth(1)
            p.setPen(border_pen); p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 13, 13)
            top_grad = QLinearGradient(0, 0, rect.width(), 0)
            top_grad.setColorAt(0.0, QColor(0, 210, 255, 0))
            top_grad.setColorAt(0.4, QColor(0, 210, 255, 28))
            top_grad.setColorAt(1.0, QColor(0, 210, 255, 0))
            p.setBrush(QBrush(top_grad)); p.setPen(Qt.NoPen)
            p.drawRect(2, 1, rect.width() - 4, 1)
            p.end()


    class JarvisFloat(QWidget):
        """Always-on-top glassmorphism JARVIS floating panel."""

        log_signal = Signal(str)
        state_signal = Signal(str)
        connector_signal = Signal(list)

        def __init__(self, orchestrator=None):
            super().__init__()
            self._orchestrator = orchestrator
            self._drag_pos = None
            self._minimized = False
            self._normal_size = QSize(320, 500)
            self._mini_size = QSize(64, 64)
            self._log_lines = []
            self._setup_ui()
            self._setup_tray()
            self._setup_shortcuts()
            self._setup_timers()
            self.log_signal.connect(self._append_log)
            self.state_signal.connect(self._on_state_change)
            self.connector_signal.connect(self._update_connectors)

        def _setup_ui(self):
            self.setWindowTitle("JARVIS MK38")
            self.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_DeleteOnClose, False)
            self.resize(self._normal_size)
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(screen.right() - self._normal_size.width() - 20,
                      screen.bottom() - self._normal_size.height() - 50)

            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(40); shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 150, 220, 80))
            self.setGraphicsEffect(shadow)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

            self._panel = GlassPanel(self)
            root.addWidget(self._panel)

            lay = QVBoxLayout(self._panel)
            lay.setContentsMargins(16, 14, 16, 14); lay.setSpacing(10)

            # Header
            hdr = QHBoxLayout(); hdr.setSpacing(8)
            self._ring = StatusRingWidget(self)
            hdr.addWidget(self._ring)
            brand = QLabel("JARVIS")
            brand.setStyleSheet("color:#00d2ff;font-weight:700;font-size:13px;font-family:'Share Tech Mono',monospace;letter-spacing:3px;")
            hdr.addWidget(brand)
            hdr.addStretch()
            self._wave = WaveformWidget(self)
            hdr.addWidget(self._wave)
            btn_min = QPushButton("--")
            btn_min.setFixedSize(22, 22); btn_min.setStyleSheet(_btn_style())
            btn_min.clicked.connect(self.toggle_minimize)
            hdr.addWidget(btn_min)
            btn_close = QPushButton("x")
            btn_close.setFixedSize(22, 22); btn_close.setStyleSheet(_btn_style(danger=True))
            btn_close.clicked.connect(self.hide)
            hdr.addWidget(btn_close)
            lay.addLayout(hdr)

            div = QFrame(); div.setFrameShape(QFrame.HLine)
            div.setStyleSheet("background:rgba(255,255,255,.07);max-height:1px;border:none;")
            lay.addWidget(div)

            self._state_lbl = QLabel("LISTENING")
            self._state_lbl.setStyleSheet("color:#00d2ff;font-size:10px;font-family:'Share Tech Mono',monospace;letter-spacing:2px;")
            lay.addWidget(self._state_lbl)

            self._log_lbl = QLabel("Awaiting command...")
            self._log_lbl.setWordWrap(True)
            self._log_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self._log_lbl.setStyleSheet(
                "color:#8899bb;font-size:11px;padding:8px;"
                "background:rgba(0,0,0,.25);border-radius:8px;"
                "border:1px solid rgba(255,255,255,.05);"
            )
            self._log_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._log_lbl.setMinimumHeight(160)
            lay.addWidget(self._log_lbl)

            ch = QLabel("CONNECTORS")
            ch.setStyleSheet("color:#4a5568;font-size:9px;font-family:'Share Tech Mono',monospace;letter-spacing:2px;margin-top:4px;")
            lay.addWidget(ch)

            self._conn_row = QHBoxLayout()
            self._conn_row.setSpacing(5); self._conn_row.setContentsMargins(0,0,0,0)
            self._conn_placeholder = QLabel("--")
            self._conn_placeholder.setStyleSheet("color:#2d3748;font-size:10px;")
            self._conn_row.addWidget(self._conn_placeholder)
            self._conn_row.addStretch()
            lay.addLayout(self._conn_row)

            inp_row = QHBoxLayout(); inp_row.setSpacing(6)
            self._input = QLineEdit()
            self._input.setPlaceholderText("Ask JARVIS...")
            self._input.setStyleSheet(
                "QLineEdit{background:rgba(255,255,255,.05);border:1px solid rgba(0,210,255,.25);"
                "border-radius:10px;color:#e6f0ff;font-size:12px;padding:6px 10px;}"
                "QLineEdit:focus{border-color:rgba(0,210,255,.55);background:rgba(0,210,255,.05);}"
            )
            self._input.returnPressed.connect(self._send_command)
            inp_row.addWidget(self._input)
            mic_btn = QPushButton("MIC")
            mic_btn.setFixedSize(36, 32); mic_btn.setStyleSheet(_btn_style(accent=True))
            mic_btn.clicked.connect(self._trigger_voice)
            inp_row.addWidget(mic_btn)
            lay.addLayout(inp_row)

        def _setup_tray(self):
            self._tray = QSystemTrayIcon(self)
            px = QPixmap(32, 32); px.fill(QColor(0, 0, 0, 0))
            p = QPainter(px); p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QBrush(QColor(0, 210, 255))); p.setPen(Qt.NoPen)
            p.drawEllipse(4, 4, 24, 24)
            p.setPen(QPen(QColor(6, 8, 16), 2)); p.setFont(QFont("Arial", 10, QFont.Bold))
            p.drawText(px.rect(), Qt.AlignCenter, "J"); p.end()
            self._tray.setIcon(QIcon(px))
            self._tray.setToolTip("JARVIS MK38")
            self._tray.activated.connect(lambda r: self.toggle_visibility() if r == QSystemTrayIcon.Trigger else None)
            menu = QMenu()
            menu.addAction("Show", self.show_normal)
            menu.addAction("Minimize", self.toggle_minimize)
            menu.addSeparator()
            menu.addAction("Quit", QApplication.quit)
            self._tray.setContextMenu(menu)
            self._tray.show()

        def _setup_shortcuts(self):
            try:
                sc = QShortcut(QKeySequence("Alt+Space"), self)
                sc.setContext(Qt.ApplicationShortcut)
                sc.activated.connect(self.toggle_visibility)
                esc = QShortcut(QKeySequence("Escape"), self)
                esc.setContext(Qt.WidgetShortcut)
                esc.activated.connect(self.toggle_minimize)
            except Exception:
                pass

        def _setup_timers(self):
            t = QTimer(self); t.timeout.connect(self._refresh_connectors); t.start(15000)
            QTimer.singleShot(800, self._refresh_connectors)

        # Public API (thread-safe)
        def write_log(self, text):
            self.log_signal.emit(str(text))

        def set_state(self, state):
            self.state_signal.emit(str(state))

        @property
        def speaking(self):
            return getattr(self, "_speaking", False)

        @speaking.setter
        def speaking(self, v):
            self._speaking = v
            self._wave.set_active(v, C.get("accent_green" if v else "accent_cyan"))

        @property
        def muted(self):
            return getattr(self, "_muted", False)

        @muted.setter
        def muted(self, v):
            self._muted = v

        @Slot(str)
        def _append_log(self, text):
            self._log_lines.append(text.strip())
            if len(self._log_lines) > 8:
                self._log_lines = self._log_lines[-8:]
            self._log_lbl.setText("\n".join(self._log_lines))

        @Slot(str)
        def _on_state_change(self, state):
            state = state.upper()
            ck = _STATE_COLORS.get(state, "text_muted")
            color = C.get(ck, C["text_muted"])
            h = f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
            icons = {"LISTENING":"LISTENING","THINKING":"THINKING","SPEAKING":"SPEAKING",
                     "EXECUTING":"EXECUTING","ERROR":"ERROR","IDLE":"IDLE"}
            self._state_lbl.setText(icons.get(state, state))
            self._state_lbl.setStyleSheet(
                f"color:{h};font-size:10px;font-family:'Share Tech Mono',monospace;letter-spacing:2px;"
            )
            self._ring.set_state(state)
            active = state in ("SPEAKING", "THINKING", "EXECUTING")
            self._wave.set_active(active, color)

        @Slot(list)
        def _update_connectors(self, connectors):
            while self._conn_row.count():
                item = self._conn_row.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            for c in connectors[:6]:
                icon = c.get("icon", "?")
                name = c.get("name", "?")[:7]
                active = c.get("configured", False)
                col = "rgba(0,210,255,.35)" if active else "rgba(255,255,255,.08)"
                txt_col = "#00d2ff" if active else "#4a5568"
                badge = QLabel(f"{icon} {name}")
                badge.setStyleSheet(
                    f"color:{txt_col};background:rgba(0,0,0,.2);"
                    f"border:1px solid {col};border-radius:10px;"
                    f"padding:1px 7px;font-size:10px;font-family:'Share Tech Mono',monospace;"
                )
                self._conn_row.addWidget(badge)

            if not connectors:
                p = QLabel("No connectors")
                p.setStyleSheet("color:#2d3748;font-size:10px;")
                self._conn_row.addWidget(p)
            self._conn_row.addStretch()

        def _send_command(self):
            text = self._input.text().strip()
            if not text: return
            self._input.clear()
            self._append_log(f"> {text}")
            self.set_state("THINKING")
            def _run():
                try:
                    if self._orchestrator:
                        resp = self._orchestrator.chat(text)
                    else:
                        import os, requests
                        p = os.environ.get("BR_SERVER_PORT", os.environ.get("PORT", "8000"))
                        hdrs = {}
                        key = os.environ.get("JARVIS_SERVER_API_KEY")
                        if key: hdrs["X-API-Key"] = key; hdrs["Authorization"] = f"Bearer {key}"
                        r = requests.post(f"http://127.0.0.1:{p}/api/chat",
                                         json={"message": text}, headers=hdrs, timeout=30)
                        resp = r.json().get("response", "")
                    self.log_signal.emit(f"< {str(resp)[:120]}")
                    self.state_signal.emit("LISTENING")
                except Exception as e:
                    self.log_signal.emit(f"[ERR] {e}")
                    self.state_signal.emit("ERROR")
            threading.Thread(target=_run, daemon=True).start()

        def _trigger_voice(self):
            self._append_log("Voice input triggered -- say 'Hey JARVIS'")
            self.set_state("LISTENING")

        def _refresh_connectors(self):
            def _fetch():
                try:
                    import os, json, requests
                    from pathlib import Path
                    p = os.environ.get("BR_SERVER_PORT", os.environ.get("PORT", "8000"))
                    hdrs = {}
                    key = os.environ.get("SERVER_API_KEY") or os.environ.get("JARVIS_SERVER_API_KEY")
                    if not key:
                        api_file = Path(__file__).resolve().parent / "config" / "api_keys.json"
                        if api_file.exists():
                            try:
                                key = json.loads(api_file.read_text(encoding="utf-8")).get("server_api_key")
                            except Exception:
                                pass
                    if key:
                        hdrs["X-API-Key"] = str(key).strip()
                        hdrs["Authorization"] = f"Bearer {str(key).strip()}"
                    r = requests.get(f"http://127.0.0.1:{p}/api/connector/status", headers=hdrs, timeout=3)
                    if r.status_code == 200:
                        self.connector_signal.emit(r.json().get("connectors", []))
                except Exception:
                    pass
            threading.Thread(target=_fetch, daemon=True).start()


        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            if event.buttons() == Qt.LeftButton and self._drag_pos:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
            super().mouseMoveEvent(event)

        def mouseDoubleClickEvent(self, event):
            self.toggle_minimize()

        def toggle_minimize(self):
            if self._minimized:
                self.show_normal()
            else:
                self._minimized = True
                for child in self._panel.findChildren(QWidget):
                    if child not in (self._wave, self._ring):
                        child.hide()
                self.resize(self._mini_size)

        def show_normal(self):
            self._minimized = False
            for child in self._panel.findChildren(QWidget):
                child.show()
            self.resize(self._normal_size)
            self.show(); self.raise_()

        def toggle_visibility(self):
            if self.isVisible(): self.hide()
            else: self.show_normal()

        def hideEvent(self, event):
            # Stop animations to conserve CPU when hidden in system tray
            if hasattr(self, "_wave") and hasattr(self._wave, "_timer"):
                self._wave._timer.stop()
            if hasattr(self, "_ring") and hasattr(self._ring, "_timer"):
                self._ring._timer.stop()
            super().hideEvent(event)

        def showEvent(self, event):
            # Resume animations when shown
            if hasattr(self, "_wave") and hasattr(self._wave, "_timer"):
                self._wave._timer.start(60)
            if hasattr(self, "_ring") and hasattr(self._ring, "_timer"):
                self._ring._timer.start(40)
            super().showEvent(event)

        def paintEvent(self, event):
            pass  # GlassPanel handles background



class HeadlessFloat:
    """Fallback for headless / no-Qt environments."""
    def __init__(self):
        self._speaking = False
        self._muted = False

    def write_log(self, text): print(f"[FLOAT] {text}")
    def set_state(self, state): print(f"[FLOAT STATE] {state}")
    @property
    def speaking(self): return self._speaking
    @speaking.setter
    def speaking(self, v):
        self._speaking = bool(v)
        print(f"[FLOAT SPEAKING] {self._speaking}")
    @property
    def muted(self): return self._muted
    @muted.setter
    def muted(self, v):
        self._muted = bool(v)
        print(f"[FLOAT MUTED] {self._muted}")


def create_float_widget(orchestrator=None):
    if not _HAS_QT:
        return HeadlessFloat()
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        app.setStyleSheet("* { font-family: 'Inter', 'Segoe UI', sans-serif; }")
        widget = JarvisFloat(orchestrator=orchestrator)
        widget.show()
        return widget
    except Exception as e:
        logger.warning("[FloatWidget] Qt init error: %s", e)
        return HeadlessFloat()


def main(argv: list[str] | None = None) -> int:
    """Canonical entry point to launch the Floating HUD Widget."""
    if not _HAS_QT:
        logger.warning("ERROR: PySide6 required. Run: pip install PySide6")
        print("ERROR: PySide6 required to run Floating Widget. Install via: pip install PySide6", file=sys.stderr)
        return 1

    app = QApplication.instance() or QApplication(sys.argv if argv is None else [sys.argv[0]] + argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet("* { font-family: 'Inter', 'Segoe UI', sans-serif; }")

    orchestrator = None
    try:
        from brjarvis.core.bootstrap import build_assistant_runtime
        rt = build_assistant_runtime()
        orchestrator = rt.orchestrator
        logger.info("[Float] JARVIS Core ready")
    except Exception as e:
        logger.debug("[Float] Standalone widget note: %s", e)

    widget = JarvisFloat(orchestrator=orchestrator)
    widget.write_log("JARVIS MK40.2 Float Widget online")
    widget.set_state("LISTENING")
    widget.show()

    logger.info("JARVIS Float Widget running. Alt+Space to toggle. Right-click tray to quit.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
