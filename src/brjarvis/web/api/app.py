"""ASGI application instance for servers that import ``brjarvis.web.api.app``."""

from __future__ import annotations

from .server import create_app

app = create_app()
