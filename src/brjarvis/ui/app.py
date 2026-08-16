# ui/app.py — JARVIS Application Wrapper
# =========================================
# Provides: JarvisUI, HeadlessJarvisUI, is_gui_available, _RootShim
from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

logger = logging.getLogger("JARVIS.UI.App")

from brjarvis.ui import _base_dir, _WIN_HIDE  # noqa: F401
from brjarvis.ui._qt import *  # noqa: F401,F403

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 148
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


def _read_full_config() -> dict:
    """Read api_keys.json config dict. Returns {} on any error."""
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


from .colors import C, qcol, current_palette
from .main_window import MainWindow
class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        exec_fn = getattr(self._app, "exec", None) or getattr(self._app, "exec_", None)
        if exec_fn:
            def _gui_excepthook(tp, val, tb):
                import traceback
                logger.error("UNHANDLED GUI EXCEPTION:\n%s", "".join(traceback.format_exception(tp, val, tb)))
            sys.excepthook = _gui_excepthook
            logger.info("Starting Qt Event Loop...")
            res = exec_fn()
            logger.info("Qt Event Loop exited with code: %s", res)
            sys.exit(res)
    def protocol(self, *_):
        pass


def is_gui_available() -> bool:
    """Check if graphical display is available and PyQt/PySide can initialize a window."""
    import os
    import sys
    import subprocess
    from ui._qt import _HAS_QT, _USE_PYSIDE6
    if not _HAS_QT:
        return False
    if os.environ.get("JARVIS_HEADLESS", "").lower() in ("true", "1"):
        return False
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        return False
    try:
        mod_name = "PySide6" if _USE_PYSIDE6 else "PyQt6"
        code = (
            "import sys; "
            f"from {mod_name}.QtWidgets import QApplication, QMainWindow; "
            f"from {mod_name}.QtCore import QTimer; "
            "app = QApplication([]); win = QMainWindow(); win.show(); "
            "timer = QTimer(app); timer.setInterval(150); timer.setSingleShot(True); "
            "timer.timeout.connect(app.quit); timer.start(); "
            "sys.exit(app.exec() if hasattr(app, 'exec') else getattr(app, 'exec_')())"
        )
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=2.5)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return True
    except Exception:
        return sys.platform == "win32"


class HeadlessJarvisUI:
    """Headless drop-in replacement for JarvisUI when display window system is unavailable."""
    def __init__(self):
        self._muted = False
        self._speaking = False
        self._current_state = "IDLE"
        self.on_text_command = None
        self.on_remote_clicked = None
        self.on_interrupt = None
        self.root = self
        self._agent_tasks = {}

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, v: bool):
        self._muted = v
        logger.info("Mute status changed to: %s", v)

    @property
    def speaking(self) -> bool:
        return self._speaking

    @speaking.setter
    def speaking(self, v: bool):
        self._speaking = v

    @property
    def _state(self) -> str:
        return self._current_state

    @property
    def current_file(self) -> str | None:
        return None

    def is_available(self) -> bool:
        return False

    def run(self):
        logger.info("Headless UI running.")

    def set_muted(self, muted: bool):
        self._muted = muted

    def set_speaking(self, speaking: bool):
        self._speaking = speaking

    def show_alert(self, title: str, text: str):
        logger.warning("[UI Alert] %s: %s", title, text)

    def prompt_user_input(self, prompt: str) -> str | None:
        logger.info("[UI Prompt] %s", prompt)
        return None

    def notify_phone_connected(self) -> None:
        logger.info("Phone connected.")

    def set_state(self, state: str):
        self._current_state = state
        logger.debug("[UI State] %s", state)

    def write_log(self, text: str):
        logger.debug("[UI Log] %s", text)

    def wait_for_api_key(self):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            logger.warning("[UI] No API key detected in environment. Prompting for API key.")
        return key

    def show_content(self, title: str, text: str):
        logger.info("--- %s ---\n%s", title, text)

    def prompt_reconfig(self):
        logger.info("[UI Prompt Reconfig] Reconfiguration requested.")

    def show_camera_frame(self, img_bytes: bytes):
        pass

    def start_camera_stream(self) -> None:
        pass

    def stop_camera_stream(self) -> None:
        pass

    def assistant_name(self) -> str:
        return "JARVIS"

    def start_speaking(self):
        self._speaking = True

    def stop_speaking(self):
        self._speaking = False

    def update_agent_task(self, task_id: str, name: str = "", status: str = "running", progress: float = 0.0, result: str = "") -> None:
        self._agent_tasks[task_id] = {
            "name": name or task_id,
            "status": status,
            "progress": progress,
            "result": result
        }
        logger.debug("[UI Task] %s: %s (%.0f%%) %s", name or task_id, status, progress * 100, result)

    def remove_agent_task(self, task_id: str) -> None:
        if task_id in self._agent_tasks:
            del self._agent_tasks[task_id]

    def clear_agent_tasks(self) -> None:
        self._agent_tasks.clear()

    def mainloop(self):
        """Standard mainloop entry point matching Tkinter/Qt shim for headless mode."""
        self.run_headless_loop()

    def run_headless_loop(self):
        logger.info("Headless Voice Assistant is active. Speak 'Hey Jarvis' or type standard commands.")
        logger.info("Type 'exit' or press Ctrl+C to quit.")
        try:
            while True:
                line = input("> ").strip()
                if line.lower() in ("exit", "quit", "q"):
                    break
                if line and self.on_text_command:
                    self.on_text_command(line)
        except (KeyboardInterrupt, EOFError):
            logger.info("Interrupted by user.")
        except Exception:
            logger.info("Console input unavailable. Running in passive hands-free voice daemon mode.")
            while True:
                time.sleep(1.0)
        finally:
            logger.info("Headless Voice Assistant shutting down...")

    def protocol(self, *_):
        pass


_GLOBAL_UI_INSTANCE: JarvisUI | None = None


class JarvisUI:
    def __init__(self, face_path: str = "face.png", size=None):
        global _GLOBAL_UI_INSTANCE
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._app.setQuitOnLastWindowClosed(True)
        self._win = MainWindow(face_path)
        self._app._main_window = self._win  # Retain strong reference on app object
        _GLOBAL_UI_INSTANCE = self          # Retain global reference
        self._win.show()
        self._win.raise_()
        self._win.activateWindow()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def speaking(self) -> bool:
        return self._win.hud.speaking

    @speaking.setter
    def speaking(self, v: bool):
        self._win.hud.speaking = v

    @property
    def _state(self) -> str:
        return self._win.hud.state

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    @property
    def on_remote_clicked(self):
        return self._win.on_remote_clicked

    @on_remote_clicked.setter
    def on_remote_clicked(self, cb):
        self._win.on_remote_clicked = cb

    @property
    def on_interrupt(self):
        return self._win.on_interrupt

    @on_interrupt.setter
    def on_interrupt(self, cb):
        self._win.on_interrupt = cb

    def notify_phone_connected(self) -> None:
        self._win.notify_phone_connected()

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def show_content(self, title: str, text: str):
        """Thread-safe: display content in the panel below the HUD."""
        self._win._content_sig.emit(title[:48], text[:4000])

    def prompt_reconfig(self):
        """Thread-safe: show the API key setup overlay (e.g. after an auth error)."""
        self._win._ready = False
        self._win._reconfig_sig.emit()

    def show_camera_frame(self, img_bytes: bytes):
        """Thread-safe: show a webcam frame in the small overlay (screen captures)."""
        self._win._camera_sig.emit(img_bytes)

    def start_camera_stream(self) -> None:
        """Thread-safe: start live camera feed in the full HUD area."""
        self._win.start_camera_stream()

    def stop_camera_stream(self) -> None:
        """Thread-safe: stop the live camera feed."""
        self._win.stop_camera_stream()

    @property
    def assistant_name(self) -> str:
        return self._win._assistant_name

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def update_agent_task(self, task_id: str, name: str, status: str, progress: float = 0.0, result: str = "") -> None:
        """Thread-safe update or add an agent task."""
        if not hasattr(self, "_agent_tasks"):
            self._agent_tasks = {}
        self._agent_tasks[task_id] = {
            "name": name,
            "status": status,
            "progress": progress,
            "result": result
        }
        if hasattr(self, "_win") and self._win:
            self._win._task_update_sig.emit(task_id, name, status, progress, result)

    def remove_agent_task(self, task_id: str) -> None:
        """Remove a completed or cancelled task."""
        if hasattr(self, "_agent_tasks") and task_id in self._agent_tasks:
            del self._agent_tasks[task_id]
        if hasattr(self, "_win") and self._win:
            self._win._task_remove_sig.emit(task_id)

    def clear_agent_tasks(self) -> None:
        """Clear all tasks."""
        if hasattr(self, "_agent_tasks"):
            self._agent_tasks.clear()
        if hasattr(self, "_win") and self._win:
            self._win._task_clear_sig.emit()



def run_voice_ui() -> None:
    """Launch the Cyberpunk Voice HUD UI."""
    try:
        from brjarvis.desktop.ui_mark import run_voice_ui as _run
        _run()
    except Exception as e:
        logger.error("Failed to run voice UI: %s", e)


if __name__ == "__main__":
    # When run directly, defer to the canonical launcher in ui_mark.py
    try:
        from ui_mark import run_voice_ui
        run_voice_ui()
    except BaseException as e:
        import traceback
        try:
            _crash = _base_dir() / "scratch" / "ui_crash.log"
            _crash.parent.mkdir(parents=True, exist_ok=True)
            with open(_crash, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
                f.write(f"\nExit: {e} ({type(e)})")
        except Exception:
            pass
        raise
