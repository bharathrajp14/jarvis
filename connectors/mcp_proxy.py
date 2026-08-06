# connectors/mcp_proxy.py — Universal MCP Server Proxy Connector
"""
Universal proxy connector that bridges JARVIS to ANY external MCP server.
Compatible with all MCP servers from the Claude marketplace and open-source community.

MCP (Model Context Protocol) is an open standard by Anthropic.
Any MCP server can be used with JARVIS — no Claude subscription needed.

Setup: Set MCP_SERVER_URLS in .env as comma-separated list of server URLs.
Example: MCP_SERVER_URLS=http://localhost:3000,http://localhost:3001
"""
from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from typing import Any, Dict, List, Optional

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.MCPProxy")


class MCPServerProxy:
    """
    Lightweight MCP client that connects to an MCP server via HTTP.
    Supports MCP HTTP/SSE transport (the most common deployment type).
    """

    def __init__(self, server_url: str, api_key: str = "", name: str = ""):
        self.url = server_url.rstrip("/")
        self.api_key = api_key
        self.name = name or server_url
        self._tools_cache: Optional[List[dict]] = None
        self._cache_lock = threading.Lock()

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-MCPProxy/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _post(self, path: str, body: dict, timeout: float = 15.0) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _get(self, path: str, timeout: float = 8.0) -> dict:
        req = urllib.request.Request(
            f"{self.url}{path}",
            headers=self._headers(),
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def list_tools(self) -> List[dict]:
        """Fetch tool definitions from the MCP server."""
        with self._cache_lock:
            if self._tools_cache is not None:
                return self._tools_cache

        tools = []
        # Try MCP standard endpoint
        for endpoint in ["/tools", "/mcp/tools", "/api/tools"]:
            try:
                data = self._get(endpoint)
                raw_tools = data.get("tools", data if isinstance(data, list) else [])
                if raw_tools:
                    tools = raw_tools
                    break
            except Exception:
                continue

        # Also try JSON-RPC 2.0 style
        if not tools:
            try:
                data = self._post("/", {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
                result = data.get("result", {})
                tools = result.get("tools", [])
            except Exception:
                pass

        with self._cache_lock:
            self._tools_cache = tools
        return tools

    def call_tool(self, name: str, args: dict) -> Any:
        """Call a tool on the MCP server."""
        # Try standard REST endpoint first
        for endpoint in ["/tools/call", "/mcp/tools/call", "/api/tools/call"]:
            try:
                result = self._post(endpoint, {"name": name, "arguments": args})
                # Extract content from MCP response format
                content = result.get("content", result)
                if isinstance(content, list):
                    # MCP returns content as list of content blocks
                    texts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                texts.append(block.get("text", ""))
                            elif block.get("type") == "image":
                                texts.append(f"[Image: {block.get('mimeType', 'image')}]")
                    return "\n".join(texts) if texts else json.dumps(content)
                return json.dumps(content) if isinstance(content, dict) else str(content)
            except Exception:
                continue

        # Try JSON-RPC 2.0
        try:
            result = self._post("/", {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            })
            rpc_result = result.get("result", {})
            content = rpc_result.get("content", rpc_result)
            if isinstance(content, list):
                texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                return "\n".join(texts) if texts else str(content)
            return str(content)
        except Exception as e:
            return f"MCP call error for '{name}': {e}"

    def ping(self) -> bool:
        for endpoint in ["/health", "/", "/tools"]:
            try:
                req = urllib.request.Request(
                    f"{self.url}{endpoint}",
                    headers=self._headers(),
                )
                with urllib.request.urlopen(req, timeout=3.0) as r:
                    return r.status < 500
            except Exception:
                continue
        return False


class MCPProxyConnector(BaseConnector):
    """
    Universal proxy connector for any external MCP server.
    Auto-discovers tools from the server and exposes them in JARVIS.
    """

    def __init__(self):
        self._servers: List[MCPServerProxy] = []
        self._all_tools: List[ConnectorTool] = []
        self._configured = False
        self._load_servers()

    def _load_servers(self) -> None:
        """Load MCP server URLs from environment."""
        urls_raw = os.environ.get("MCP_SERVER_URLS", "").strip()
        if not urls_raw:
            return

        for entry in urls_raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            # Support "name=url:key" format
            name, api_key = "", ""
            if "=" in entry and "://" not in entry.split("=")[0]:
                parts = entry.split("=", 1)
                name = parts[0].strip()
                entry = parts[1].strip()
            if ":key=" in entry:
                entry, api_key = entry.split(":key=", 1)

            proxy = MCPServerProxy(entry, api_key=api_key, name=name or entry)
            if proxy.ping():
                self._servers.append(proxy)
                logger.info("MCPProxy: Connected to server %s", proxy.url)
            else:
                logger.warning("MCPProxy: Server unreachable: %s", proxy.url)

        self._configured = len(self._servers) > 0
        if self._configured:
            self._build_tool_list()

    def _build_tool_list(self) -> None:
        """Fetch and cache tools from all connected MCP servers."""
        for server in self._servers:
            try:
                server_tools = server.list_tools()
                for t in server_tools:
                    name = t.get("name", "")
                    description = t.get("description", "")
                    parameters = t.get("inputSchema") or t.get("parameters") or {
                        "type": "object", "properties": {}
                    }
                    if name:
                        self._all_tools.append(ConnectorTool(
                            name=f"{server.name}_{name}",
                            description=f"[{server.name}] {description}",
                            parameters=parameters,
                            requires_auth=False,
                        ))
                logger.info("MCPProxy: Loaded %d tools from %s", len(server_tools), server.url)
            except Exception as e:
                logger.warning("MCPProxy: Failed to load tools from %s: %s", server.url, e)

    @property
    def connector_id(self) -> str:
        return "mcp_proxy"

    @property
    def display_name(self) -> str:
        return f"MCP Server Proxy ({len(self._servers)} servers)"

    @property
    def description(self) -> str:
        if not self._servers:
            return "Universal proxy to any MCP server (not configured)"
        server_names = ", ".join(s.name for s in self._servers[:3])
        return f"Connected to external MCP servers: {server_names}"

    @property
    def icon(self) -> str:
        return "🔌"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_configured(self) -> bool:
        return self._configured

    @property
    def auth_hint(self) -> str:
        return (
            "Add to your .env file:\n"
            "MCP_SERVER_URLS=http://localhost:3000,http://my-mcp-server.com\n\n"
            "Any MCP server works — run local MCP servers using:\n"
            "  npx @modelcontextprotocol/server-filesystem\n"
            "  npx @modelcontextprotocol/server-github\n"
            "  npx @modelcontextprotocol/server-sqlite\n"
            "  (and 200+ others from the MCP marketplace)"
        )

    def list_tools(self) -> List[ConnectorTool]:
        return self._all_tools

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        # Resolve server + real tool name
        for server in self._servers:
            prefix = f"{server.name}_"
            if tool_name.startswith(prefix):
                real_name = tool_name[len(prefix):]
                return server.call_tool(real_name, args)

        # Try all servers
        for server in self._servers:
            try:
                result = server.call_tool(tool_name, args)
                if not result.startswith("MCP call error"):
                    return result
            except Exception:
                continue
        return f"❌ Tool '{tool_name}' not found on any connected MCP server."

    def health_check(self) -> bool:
        return any(s.ping() for s in self._servers)

    def add_server(self, url: str, name: str = "", api_key: str = "") -> str:
        """Dynamically add a new MCP server at runtime."""
        proxy = MCPServerProxy(url, api_key=api_key, name=name or url)
        if proxy.ping():
            self._servers.append(proxy)
            self._configured = True
            self._build_tool_list()
            return f"✅ MCP server '{url}' connected. {len(proxy.list_tools())} tools loaded."
        return f"❌ Could not connect to MCP server: {url}"
