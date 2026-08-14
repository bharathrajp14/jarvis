# server.py — BR JARVIS Production Server Entrypoint
"""
FastAPI Server Entrypoint for BR JARVIS.
Mounts the modular api/ application layer with full backwards compatibility and PID management.
"""
from __future__ import annotations

import atexit
import logging
import os
import platform
import socket
import sys
from pathlib import Path

# Auto-reroute from Python 3.14 alpha to stable Python 3.12 if requested
if __name__ == "__main__" and sys.version_info >= (3, 14) and sys.platform == "win32" and not os.environ.get("JARVIS_IGNORE_PY314"):
    import shutil
    import subprocess
    _py_cmd = shutil.which("py")
    if _py_cmd:
        for _ver in ("-3.12", "-3.13", "-3.11"):
            _chk = subprocess.run([_py_cmd, _ver, "--version"], capture_output=True)
            if _chk.returncode == 0:
                print(f"[server] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}...")
                os.environ["JARVIS_IGNORE_PY314"] = "1"
                _res = subprocess.run([_py_cmd, _ver] + sys.argv)
                sys.exit(_res.returncode)

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn
from api.server import create_app
from api.state import (
    ORCHESTRATOR,
    SERVER_API_KEY,
    CONFIG_DIR,
    WEB_DIR,
    ACTIVE_WEBSOCKETS,
    get_ws_lock,
    get_orchestrator
)

# Canonical FastAPI application instance
app = create_app()

logger = logging.getLogger("JARVIS.Server")

PID_FILE = BASE_DIR / ".jarvis_server.pid"


def _cleanup_pid():
    try:
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


atexit.register(_cleanup_pid)


def _check_port_available(host: str, port: int) -> bool:
    """Verify if target port is available without killing arbitrary processes."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def main():
    port = int(os.environ.get("BR_SERVER_PORT", 8000))
    host = os.environ.get("BR_SERVER_HOST", "127.0.0.1")

    # Record PID
    try:
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass

    # Verify port availability safely
    if not _check_port_available(host, port):
        logger.error(
            "Port %s:%s is already in use by another process. Please terminate the competing service or configure BR_SERVER_PORT.",
            host, port
        )
        print(f"\n[ERROR] Port {host}:{port} is already in use by another process.")
        print(f"        Please free port {port} or set BR_SERVER_PORT=<new_port> in your environment or .env file.\n")
        sys.exit(1)

    logger.info("Exposing BR JARVIS Autonomous Control Plane on http://%s:%s", host, port)

    # Boot proactive listener if configured
    try:
        from actions.proactive_listener import get_proactive_listener
        listener = get_proactive_listener()
        listener.start(poll_interval=30)
    except Exception as exc:
        logger.debug("Proactive listener boot note: %s", exc)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
