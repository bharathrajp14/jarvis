#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui_mark.py — BR JARVIS MK38 Cyberpunk HUD Entry Point
======================================================
Unified launcher for the Cyberpunk HUD GUI + Hands-Free Voice Engine
+ FastAPI backend server.

Requires Python 3.12+ (stable). Python 3.14 alpha auto-reroutes to 3.12.

Run:
    py -3.12 ui_mark.py
"""

from __future__ import annotations

import atexit
import logging
import os
import platform
import signal
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Python version guard & automatic reroute to stable Python 3.12
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__" and sys.version_info >= (3, 14) and sys.platform == "win32" and not os.environ.get("JARVIS_IGNORE_PY314"):
    import shutil
    import subprocess
    _py_cmd = shutil.which("py")
    if _py_cmd:
        for _ver in ("-3.12", "-3.13", "-3.11"):
            _chk = subprocess.run([_py_cmd, _ver, "--version"], capture_output=True)
            if _chk.returncode == 0:
                print(f"[ui_mark] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}...")
                os.environ["JARVIS_IGNORE_PY314"] = "1"
                _res = subprocess.run([_py_cmd, _ver] + sys.argv)
                sys.exit(_res.returncode)

# ─────────────────────────────────────────────────────────────────────────────
# 2.  Ensure project root is in sys.path so all project imports resolve
# ─────────────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# 3.  Windows console / encoding hygiene
# ─────────────────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from ui import setup_qt_paths
setup_qt_paths()


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Logging setup — structured, coloured-friendly, goes to stdout + file
# ─────────────────────────────────────────────────────────────────────────────
_LOG_DIR = _ROOT / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,
    format="[%(levelname)s %(asctime)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_DIR / "ui_mark.log", encoding="utf-8", mode="a"),
    ],
)
log = logging.getLogger("ui_mark")

# ─────────────────────────────────────────────────────────────────────────────
# 5.  Qt detection (PySide6 preferred, PyQt6 fallback)
# ─────────────────────────────────────────────────────────────────────────────
_USE_PYSIDE6 = False
try:
    import PySide6  # type: ignore[import-not-found] # noqa: F401
    _USE_PYSIDE6 = True
except ImportError:
    try:
        import PyQt6  # type: ignore[import-not-found] # noqa: F401
    except ImportError:
        print(
            "[ui_mark] ❌ Neither PySide6 nor PyQt6 is installed.\n"
            "         Run: py -3.14 -m pip install PySide6",
            file=sys.stderr,
        )

# ─────────────────────────────────────────────────────────────────────────────
# 6.  Import UI components — these are the only public exports of this module
# ─────────────────────────────────────────────────────────────────────────────
from ui.colors import C, apply_ui_accent, current_palette, retheme_all_widgets, qcol  # noqa: E402
from ui.widgets import (  # noqa: E402
    HudCanvas, MetricBar, LogWidget,
    SubAgentTaskWidget, SubAgentTaskPanel, FileDropZone,
)
from ui.overlays import (  # noqa: E402
    SetupOverlay, HueWheel, CustomizeOverlay, ClipboardPanel, RemoteKeyOverlay,
)
from ui.main_window import MainWindow  # noqa: E402
from ui.app import (  # noqa: E402
    JarvisUI, HeadlessJarvisUI, is_gui_available, _RootShim,
)

# ─────────────────────────────────────────────────────────────────────────────
# 7.  Server port helper
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_PORT = 8000


def _is_jarvis_running(port: int) -> bool:
    """Check if an active JARVIS backend server is responding on the given port."""
    import urllib.request
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health", headers={"User-Agent": "JARVIS-Ping"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("status") in ("online", "ok", "degraded")
    except Exception:
        pass
    return False


def _find_available_jarvis_port(preferred_port: int = 8000) -> int:
    """Return preferred_port if free or running JARVIS, otherwise find a free fallback port."""
    if _is_jarvis_running(preferred_port) or _port_free(preferred_port):
        return preferred_port
    
    for p in (8080, 8088, 8888, 5000, 8001, 8002):
        if _is_jarvis_running(p) or _port_free(p):
            return p
    return preferred_port


def _server_port() -> int:
    """Read backend port from environment or auto-detect available port."""
    env_p = os.environ.get("BR_SERVER_PORT") or os.environ.get("PORT")
    if env_p and env_p.isdigit():
        p = int(env_p)
        if _is_jarvis_running(p) or _port_free(p):
            return p
    p = _find_available_jarvis_port(_DEFAULT_PORT)
    os.environ["BR_SERVER_PORT"] = str(p)
    return p


def _port_free(port: int) -> bool:
    """Return True if the given TCP port is not already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) != 0


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Background server thread
# ─────────────────────────────────────────────────────────────────────────────
def _start_backend_server() -> threading.Thread:
    """
    Launch the FastAPI/Uvicorn backend server in a daemon thread.

    - Verifies whether port is running JARVIS or occupied by a foreign process.
    - Uses fallback port (e.g. 8080) if preferred port is occupied by another app.
    """
    port = _server_port()

    def _worker() -> None:
        if _is_jarvis_running(port):
            print(f"[Server] ⚡ Embedded JARVIS backend active on http://127.0.0.1:{port}")
            return

        if not _port_free(port):
            print(f"[Server] Port {port} occupied by foreign application. Switching to fallback port...")
            alt_port = _find_available_jarvis_port(port + 1)
            os.environ["BR_SERVER_PORT"] = str(alt_port)
            port_to_use = alt_port
        else:
            port_to_use = port

        try:
            import uvicorn  # type: ignore[import-not-found]
            from server import app as _fastapi_app  # type: ignore[import-not-found]
            print(f"[Server] ⚙ Starting embedded JARVIS backend on http://127.0.0.1:{port_to_use}")
            uvicorn.run(
                _fastapi_app,
                host="127.0.0.1",
                port=port_to_use,
                log_level="warning",
                access_log=False,
            )
        except ImportError as e:
            print(f"[Server] Dependency missing — web dashboard unavailable: {e}")
        except Exception as e:
            log.warning("Backend server exited: %s", e)

    t = threading.Thread(target=_worker, daemon=True, name="backend-server")
    t.start()
    return t


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Background voice-assistant thread
# ─────────────────────────────────────────────────────────────────────────────
def _start_voice_worker(ui: JarvisUI | HeadlessJarvisUI) -> threading.Thread:
    """
    Launch BRVoiceAssistant in a daemon thread using a fresh asyncio event loop.

    Using asyncio.run() (Python 3.12) gives each thread a clean loop with
    proper cleanup rather than relying on deprecated get_event_loop().
    """
    import asyncio

    def _worker() -> None:
        try:
            from voice.assistant import BRVoiceAssistant
            assistant = BRVoiceAssistant(ui)
            asyncio.run(assistant.run())
        except ImportError as e:
            print(f"[Voice] Import error — voice engine unavailable: {e}")
        except KeyboardInterrupt:
            pass
        except Exception as e:
            log.error("Voice worker crashed: %s", e, exc_info=True)
            # Surface the error to the UI log so the user sees it
            try:
                ui.write_log(f"[Voice Error] {e}")
                ui.set_state("ERROR")
            except Exception:
                pass

    t = threading.Thread(target=_worker, daemon=True, name="voice-engine")
    t.start()
    return t


# ─────────────────────────────────────────────────────────────────────────────
# 10.  Graceful shutdown hook
# ─────────────────────────────────────────────────────────────────────────────
def _install_signal_handlers() -> None:
    """Install SIGINT/SIGTERM handlers for clean shutdown on Ctrl+C or kill."""
    def _shutdown(sig: int, _frame) -> None:  # type: ignore[type-arg]
        print(f"\n[ui_mark] Received signal {sig} — shutting down gracefully...")
        sys.exit(0)

    for _sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(_sig, _shutdown)
        except (OSError, ValueError):
            pass  # Signal not available in this environment


# ─────────────────────────────────────────────────────────────────────────────
# 11.  Crash logger
# ─────────────────────────────────────────────────────────────────────────────
_CRASH_LOG = _ROOT / "scratch" / "ui_crash.log"


def _write_crash_log(exc: BaseException) -> None:
    """Write a full traceback + Python version to scratch/ui_crash.log."""
    try:
        _CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _CRASH_LOG.open("w", encoding="utf-8") as fh:
            fh.write(f"Python {sys.version}\n")
            fh.write(f"Platform: {platform.platform()}\n\n")
            traceback.print_exc(file=fh)
            fh.write(f"\nExit: {exc!r} ({type(exc).__name__})\n")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 12.  Main launcher  (replaces the old run_voice_ui() in ui/app.py)
# ─────────────────────────────────────────────────────────────────────────────
def run_voice_ui() -> None:
    """
    Full-stack launch sequence:

    1. Detect GUI availability → pick JarvisUI or HeadlessJarvisUI.
    2. Start FastAPI backend server in a daemon thread.
    3. Start BRVoiceAssistant in a daemon thread.
    4. Block on the Qt (or headless stdin) event loop.
    """
    _install_signal_handlers()

    # ── GUI vs headless decision ──────────────────────────────────────────────
    if is_gui_available():
        print("▶ Starting BR JARVIS Cyberpunk HUD UI with Hands-Free Voice Engine...")
        ui: JarvisUI | HeadlessJarvisUI = JarvisUI()
    else:
        print("▶ Starting BR JARVIS Headless Voice Assistant (no display detected)...")
        ui = HeadlessJarvisUI()

    # ── Backend server (web dashboard) ────────────────────────────────────────
    _srv_thread = _start_backend_server()

    # ── Voice engine ──────────────────────────────────────────────────────────
    _voice_thread = _start_voice_worker(ui)

    # ── Register cleanup ──────────────────────────────────────────────────────
    @atexit.register
    def _cleanup() -> None:
        print("[ui_mark] Shutdown complete.")

    # ── Block on event loop ───────────────────────────────────────────────────
    if hasattr(ui, "root") and hasattr(ui.root, "mainloop"):
        ui.root.mainloop()
    else:
        # Fallback: keep the main thread alive until daemon threads finish
        try:
            while _voice_thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[ui_mark] Interrupted by user.")


# ─────────────────────────────────────────────────────────────────────────────
# 13.  Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run_voice_ui()
    except SystemExit:
        # Normal exit from Qt event loop — do not log as a crash
        raise
    except KeyboardInterrupt:
        print("\n[ui_mark] Stopped by user.")
    except BaseException as exc:  # pylint: disable=broad-except
        _write_crash_log(exc)
        print(
            f"[ui_mark] ❌ Fatal error: {exc!r}\n"
            f"          Full trace written to: {_CRASH_LOG}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
