# connectors/__init__.py — BR JARVIS Connector Hub Package
"""
JARVIS Connector Hub — Multi-source plugin ecosystem.

Provides free, plug-and-play connectors to popular services:
  Zero-Setup: Wikipedia, Weather, DuckDuckGo, RSS, Local Filesystem
  API Key:    GitHub, YouTube, Notion, Slack, Tavily, Any MCP Server
  OAuth2:     Gmail, Google Drive

Usage:
    from brjarvis.connectors import get_hub
    hub = get_hub()
    result = hub.call("wikipedia", "search", {"query": "quantum computing"})
"""
from __future__ import annotations

from .hub import ConnectorHub, get_hub

__all__ = ["ConnectorHub", "get_hub"]
