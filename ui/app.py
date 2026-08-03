from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
    for _mod_name in ("PySide6", "PyQt6", "PyQt5"):
        try:
            _m = __import__(_mod_name)
            _mod_dir = os.path.dirname(_m.__file__)
            _plugins_dir = os.path.join(_mod_dir, "plugins")
            _platforms_dir = os.path.join(_plugins_dir, "platforms")
            os.environ["QT_PLUGIN_PATH"] = _plugins_dir
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _platforms_dir
            if hasattr(os, "add_dll_directory"):
                for _d in (_mod_dir, _plugins_dir, _platforms_dir):
                    if os.path.exists(_d):
                        try:
                            os.add_dll_directory(_d)
                        except Exception:
                            pass
            break
        except ImportError:
            continue
else:
    _WIN_HIDE: dict = {}

_USE_PYSIDE6 = False
try:
    import PySide6
    _USE_PYSIDE6 = True
except ImportError:
    pass

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

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"


def _read_full_config() -> dict:
    """Read api_keys.json config dict. Returns {} on any error."""
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 148
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"



from ui.colors import C, qcol, current_palette
from ui.main_window import MainWindow
class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        exec_fn = getattr(self._app, "exec", None) or getattr(self._app, "exec_", None)
        if exec_fn:
            def _gui_excepthook(tp, val, tb):
                import traceback
                print("=" * 60)
                print("❌ UNHANDLED GUI EXCEPTION:")
                traceback.print_exception(tp, val, tb)
                print("=" * 60)
                sys.stdout.flush()
                sys.stderr.flush()
            sys.excepthook = _gui_excepthook
            print("🚀 Starting Qt Event Loop...")
            res = exec_fn()
            print(f"⏹ Qt Event Loop exited with code: {res}")
            sys.exit(res)
    def protocol(self, *_):
        pass


def is_gui_available() -> bool:
    """Check if graphical display is available and PyQt/PySide can initialize a window."""
    import os
    import sys
    import subprocess
    if os.environ.get("JARVIS_HEADLESS", "").lower() in ("true", "1"):
        return False
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        return False
    try:
        mod_name = "PySide6" if _USE_PYSIDE6 else "PyQt6"
        code = (
            f"import sys; from {mod_name}.QtWidgets import QApplication, QMainWindow; "
            f"from {mod_name}.QtCore import QTimer; "
            f"app = QApplication([]); win = QMainWindow(); win.show(); "
            f"timer = QTimer(app); timer.setInterval(150); timer.setSingleShot(True); "
            f"timer.timeout.connect(app.quit); timer.start(); "
            f"sys.exit(app.exec() if hasattr(app, 'exec') else app.exec_())"
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
        print(f"[UI] Mute status changed to: {v}")

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

    def notify_phone_connected(self) -> None:
        print("[UI] Phone connected.")

    def set_state(self, state: str):
        self._current_state = state
        print(f"[UI State] {state}")

    def write_log(self, text: str):
        print(f"[UI Log] {text}")

    def wait_for_api_key(self):
        pass

    def show_content(self, title: str, text: str):
        print(f"\n--- {title} ---\n{text}\n----------------")

    def prompt_reconfig(self):
        pass

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

    def update_agent_task(self, task_id: str, name: str, status: str, progress: float = 0.0, result: str = "") -> None:
        self._agent_tasks[task_id] = {"name": name, "status": status, "progress": progress}
        print(f"[UI Task] {name}: {status} ({progress*100}%)")

    def remove_agent_task(self, task_id: str) -> None:
        if task_id in self._agent_tasks:
            del self._agent_tasks[task_id]

    def clear_agent_tasks(self) -> None:
        self._agent_tasks.clear()

    def mainloop(self):
        print("[UI] Headless Voice Assistant is active. Speak 'Hey Jarvis' or type standard commands.")
        print("[UI] Type 'exit' or press Ctrl+C to quit.")
        try:
            while True:
                cmd = input()
                if cmd.strip().lower() in ("exit", "quit"):
                    break
                if self.on_text_command:
                    self.on_text_command(cmd)
        except KeyboardInterrupt:
            print("[UI] Interrupted by user.")
        except EOFError:
            print("[UI] Console input unavailable. Running in passive hands-free voice daemon mode.")
            try:
                while True:
                    time.sleep(10)
            except KeyboardInterrupt:
                pass
        print("[UI] Headless Voice Assistant shutting down...")

    def protocol(self, *_):
        pass


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


def run_voice_ui():
    """Launch Cyberpunk HUD GUI alongside background Hands-Free BRVoiceAssistant."""
    if is_gui_available():
        ui = JarvisUI()
        print("▶ Starting BR JARVIS Cyberpunk HUD UI with Hands-Free Voice Engine...")
    else:
        ui = HeadlessJarvisUI()
        print("▶ Starting BR JARVIS Headless Voice Assistant...")

    # Start FastAPI backend server in background so web dashboard works
    def server_worker():
        try:
            import uvicorn
            from server import app as fastapi_app
            port = int(os.environ.get("PORT", os.environ.get("BR_SERVER_PORT", "8000")))
            uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")
        except Exception as e:
            print(f"[Server] Backend server note: {e}")

    server_t = threading.Thread(target=server_worker, daemon=True, name="backend-server")
    server_t.start()

    def voice_worker():
        import asyncio
        try:
            from voice.assistant import BRVoiceAssistant
            assistant = BRVoiceAssistant(ui)
            asyncio.run(assistant.run())
        except Exception as e:
            print(f"[VoiceUI] Voice assistant worker note: {e}")

    t = threading.Thread(target=voice_worker, daemon=True)
    t.start()

    if hasattr(ui, "root") and hasattr(ui.root, "mainloop"):
        ui.root.mainloop()


if __name__ == "__main__":
    try:
        run_voice_ui()
    except BaseException as e:
        import traceback
        try:
            with open("scratch/ui_crash.log", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
                f.write(f"\nExit: {e} ({type(e)})")
        except Exception:
            pass
        raise