# src/brjarvis/apps/web.py — Canonical Web Server Entry Point for BR JARVIS MK40.2+
from __future__ import annotations

import os
import sys
import uvicorn

def main() -> int:
    port = int(os.environ.get("PORT", os.environ.get("BR_SERVER_PORT", "8000")))
    host = os.environ.get("HOST", "127.0.0.1")
    from apps.web.api.app import app
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0

if __name__ == "__main__":
    sys.exit(main())
