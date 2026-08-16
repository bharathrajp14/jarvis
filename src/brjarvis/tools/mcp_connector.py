# tools/mcp_connector.py
# Compatible with any MCP server (Claude Desktop, Open Claw, Paperclip, custom)
from __future__ import annotations

import logging
import httpx
from typing import Dict, Any
from .registry import register_tool

logger = logging.getLogger(__name__)


class MCPConnector:
    """Compatible with any Model Context Protocol (MCP) server."""

    def __init__(self, server_url: str, api_key: str | None = None, timeout: float = 10.0):
        self.url = server_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.timeout = timeout

    def list_tools(self) -> list[dict]:
        try:
            r = httpx.get(f"{self.url}/tools", headers=self.headers, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return data.get("tools", [])
            return []
        except Exception as e:
            logger.warning(f"[MCPConnector] List tools error ({self.url}): {e}")
            return []

    def call_tool(self, name: str, args: dict) -> dict:
        payload = {"name": name, "arguments": args}
        try:
            r = httpx.post(f"{self.url}/tools/call", json=payload, headers=self.headers, timeout=self.timeout)
            if r.status_code == 200:
                return r.json()
            return {"error": f"MCP server error ({r.status_code}): {r.text}"}
        except Exception as e:
            return {"error": f"MCP connection error: {e}"}


@register_tool(
    name="mcp_call_tool",
    description="Connect to an external Model Context Protocol (MCP) server and execute a tool call.",
    parameters={
        "type": "object",
        "properties": {
            "server_url": {"type": "string", "description": "MCP server base URL"},
            "tool_name": {"type": "string", "description": "Target tool name on MCP server"},
            "args": {"type": "object", "description": "Tool parameters payload"}
        },
        "required": ["server_url", "tool_name"]
    }
)
def mcp_call_tool_action(args: Dict[str, Any]) -> str:
    """Execute tool on external MCP server."""
    url = str(args.get("server_url") or args.get("url") or "").strip()
    name = str(args.get("tool_name") or args.get("name") or "").strip()
    payload = args.get("args") or args.get("arguments") or {}
    api_key = args.get("api_key")

    if not url or not name:
        return "ERROR: 'server_url' and 'tool_name' parameters are required."

    connector = MCPConnector(server_url=url, api_key=api_key)
    res = connector.call_tool(name, payload if isinstance(payload, dict) else {})
    import json
    return json.dumps(res, indent=2)
