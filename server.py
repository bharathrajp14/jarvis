# server.py — BR JARVIS Production Server Entrypoint
"""
FastAPI Server Entrypoint for BR JARVIS.
Mounts the modular api/ application layer with full backwards compatibility.
"""
from __future__ import annotations

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path

# Auto-reroute from Python 3.14 alpha to stable Python 3.12 if requested
if __name__ == "__main__" and sys.version_info >= (3, 14) and sys.platform == "win32" and not os.environ.get("JARVIS_IGNORE_PY314"):
    import shutil
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

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
    BASE_DIR,
    CONFIG_DIR,
    WEB_DIR,
    ACTIVE_WEBSOCKETS,
    get_ws_lock,
    get_orchestrator
)

# Canonical FastAPI application instance
app = create_app()

logger = logging.getLogger("JARVIS.Server")


def main():
    port = int(os.environ.get("BR_SERVER_PORT", 8000))
    host = os.environ.get("BR_SERVER_HOST", "127.0.0.1")

    # Clean up stale processes on Windows if port is occupied
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) != os.getpid():
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                        logger.info("[Server] Killed stale process PID %s on port %s", pid, port)
        except Exception:
            pass

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
