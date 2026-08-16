# connectors/mcp_proxy.py — Universal MCP Server Proxy Connector
"""
Universal Model Context Protocol (MCP) proxy connector for BR JARVIS.
Compatible with any MCP server (HTTP/SSE or stdio).
Allows JARVIS to dynamically discover, bridge, and execute tools from external MCP servers.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.MCPProxy")

from brjarvis.core.paths import paths

_CONFIG_PATH = paths.CONFIG_ROOT / "mcp_servers.json"


class MCPServerProxy:
    """
    Lightweight MCP client that connects to an MCP server via HTTP/SSE.
    """

    def __init__(self, server_url: str, api_key: str = "", name: str = ""):
        self.url = server_url.rstrip("/")
        self.api_key = api_key
        self.name = name or self._infer_name(server_url)
        self._tools_cache: Optional[List[dict]] = None
        self._cache_lock = threading.Lock()

    def _infer_name(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        return parsed.hostname or url.replace("http://", "").replace("https://", "").replace("/", "_")

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-MCPProxy/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _post(self, path: str, body: dict, timeout: float = 10.0) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _get(self, path: str, timeout: float = 6.0) -> dict:
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
        for endpoint in ["/tools", "/mcp/tools", "/api/tools"]:
            try:
                data = self._get(endpoint)
                raw_tools = data.get("tools", data if isinstance(data, list) else [])
                if raw_tools:
                    tools = raw_tools
                    break
            except Exception:
                continue

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
        for endpoint in ["/tools/call", "/mcp/tools/call", "/api/tools/call"]:
            try:
                result = self._post(endpoint, {"name": name, "arguments": args})
                content = result.get("content", result)
                if isinstance(content, list):
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
                with urllib.request.urlopen(req, timeout=2.5) as r:
                    return r.status < 500
            except Exception:
                continue
        return False


class MCPProxyConnector(BaseConnector):
    """
    Universal proxy connector for external Model Context Protocol (MCP) servers.
    Provides bridge and management tools natively.
    """

    def __init__(self):
        self._servers: Dict[str, MCPServerProxy] = {}
        self._load_all_servers()

    def _load_all_servers(self) -> None:
        """Load servers from config/mcp_servers.json and environment."""
        # 1. From config file
        if _CONFIG_PATH.exists():
            try:
                data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                for s in data.get("servers", []):
                    url = s.get("url", "").strip()
                    name = s.get("name", "").strip()
                    key = s.get("api_key", "").strip()
                    if url:
                        self._servers[name or url] = MCPServerProxy(url, api_key=key, name=name)
            except Exception as e:
                logger.warning("Failed to load mcp_servers.json: %e", e)

        # 2. From MCP_SERVER_URLS env
        urls_raw = os.environ.get("MCP_SERVER_URLS", "").strip()
        if urls_raw:
            for entry in urls_raw.split(","):
                entry = entry.strip()
                if not entry:
                    continue
                name, api_key = "", ""
                if "=" in entry and "://" not in entry.split("=")[0]:
                    parts = entry.split("=", 1)
                    name = parts[0].strip()
                    entry = parts[1].strip()
                if ":key=" in entry:
                    entry, api_key = entry.split(":key=", 1)
                self._servers[name or entry] = MCPServerProxy(entry, api_key=api_key, name=name)

    def _save_servers_to_file(self) -> None:
        try:
            _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            existing = {}
            if _CONFIG_PATH.exists():
                try:
                    existing = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                except Exception:
                    pass
            existing["servers"] = [
                {"name": s.name, "url": s.url, "api_key": s.api_key}
                for s in self._servers.values()
            ]
            _CONFIG_PATH.write_text(json.dumps(existing, indent=4), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save mcp_servers.json: %s", e)

    @property
    def connector_id(self) -> str:
        return "mcp_proxy"

    @property
    def display_name(self) -> str:
        count = len(self._servers)
        return f"MCP Server Proxy ({count} server{'s' if count != 1 else ''})" if count > 0 else "MCP Server Proxy"

    @property
    def description(self) -> str:
        if not self._servers:
            return "Universal Model Context Protocol bridge: connect, manage and run tools on any MCP server."
        names = ", ".join(list(self._servers.keys())[:3])
        return f"Universal MCP bridge ({len(self._servers)} registered: {names})"

    @property
    def icon(self) -> str:
        return "🔌"

    @property
    def requires_auth(self) -> bool:
        return False

    @property
    def is_configured(self) -> bool:
        return True

    @property
    def auth_hint(self) -> str:
        return "Add any MCP server endpoint (e.g. http://localhost:3000) using the + Add Server tool or in config/mcp_servers.json."

    def list_tools(self) -> List[ConnectorTool]:
        tools = [
            ConnectorTool(
                name="list_servers",
                description="List all registered MCP servers and their real-time connectivity status",
                parameters={"type": "object", "properties": {}},
            ),
            ConnectorTool(
                name="add_server",
                description="Register a new external MCP server URL (e.g. 'http://localhost:3000')",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "MCP server HTTP/SSE URL (e.g. http://localhost:3000)"},
                        "name": {"type": "string", "description": "Short identifier/name for this server"},
                        "api_key": {"type": "string", "description": "Optional Bearer auth token"},
                    },
                    "required": ["url"],
                },
            ),
            ConnectorTool(
                name="remove_server",
                description="Disconnect and remove an MCP server by name or URL",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name or URL of the server to remove"},
                    },
                    "required": ["name"],
                },
            ),
            ConnectorTool(
                name="call_tool",
                description="Execute any tool on a connected MCP server",
                parameters={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Target tool name on the MCP server"},
                        "args": {"type": "object", "description": "JSON arguments for the tool call", "default": {}},
                        "server_name": {"type": "string", "description": "Optional target server name if multiple exist"},
                    },
                    "required": ["tool_name"],
                },
            ),
            ConnectorTool(
                name="list_tools",
                description="Inspect all tools provided by connected MCP servers",
                parameters={"type": "object", "properties": {}},
            ),
        ]

        # Also expose dynamic tools from connected servers
        for s_name, server in self._servers.items():
            try:
                server_tools = server.list_tools()
                for t in server_tools:
                    tname = t.get("name", "")
                    if tname:
                        tools.append(ConnectorTool(
                            name=f"{s_name}_{tname}",
                            description=f"[{s_name}] {t.get('description', '')}",
                            parameters=t.get("inputSchema") or t.get("parameters") or {"type": "object", "properties": {}},
                        ))
            except Exception:
                pass

        return tools

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        norm = tool_name.lower().replace("mcp_proxy_", "").replace("mcp_", "")

        if norm in ("list_servers", "servers", "status"):
            if not self._servers:
                return "🔌 **MCP Proxy Bridge: 0 external servers registered.**\nUse `add_server` or the UI to connect an MCP server (e.g. `http://localhost:3000`)."
            lines = [f"🔌 **Registered MCP Servers ({len(self._servers)}):**\n"]
            for name, s in self._servers.items():
                alive = s.ping()
                status_icon = "🟢 Connected" if alive else "🔴 Offline"
                tools_cnt = len(s.list_tools()) if alive else 0
                lines.append(f"• **{name}** — `{s.url}` ({status_icon}, {tools_cnt} tools)")
            return "\n".join(lines)

        elif norm in ("add_server", "add", "connect"):
            url = str(args.get("url") or args.get("server_url") or "").strip()
            name = str(args.get("name") or "").strip()
            api_key = str(args.get("api_key") or args.get("token") or "").strip()
            if not url:
                return "Error: 'url' parameter is required to add an MCP server."
            proxy = MCPServerProxy(url, api_key=api_key, name=name)
            self._servers[proxy.name] = proxy
            self._save_servers_to_file()
            alive = proxy.ping()
            tools_cnt = len(proxy.list_tools()) if alive else 0
            status_text = f"🟢 Connected ({tools_cnt} tools found)" if alive else "⚠️ Registered (server currently unreachable)"
            return f"🔌 MCP Server '{proxy.name}' ({url}) registered: {status_text}."

        elif norm in ("remove_server", "remove", "delete", "disconnect"):
            target = str(args.get("name") or args.get("url") or "").strip()
            if not target:
                return "Error: 'name' or 'url' is required to remove an MCP server."
            removed = False
            for k in list(self._servers.keys()):
                if k.lower() == target.lower() or self._servers[k].url.lower() == target.lower():
                    del self._servers[k]
                    removed = True
            if removed:
                self._save_servers_to_file()
                return f"🔌 MCP server '{target}' removed successfully."
            return f"MCP server '{target}' not found."

        elif norm in ("list_tools", "tools"):
            if not self._servers:
                return "🔌 No external MCP servers connected. Register one to view its tools."
            lines = ["🔌 **Available MCP Server Tools:**\n"]
            found = False
            for name, s in self._servers.items():
                tools = s.list_tools()
                if tools:
                    found = True
                    lines.append(f"**[{name}]** ({s.url}):")
                    for t in tools:
                        lines.append(f"  • `{t.get('name')}`: {t.get('description', 'No description')}")
            return "\n".join(lines) if found else "🔌 No tools discovered from connected servers."

        elif norm in ("call_tool", "call", "run", "execute"):
            target_tool = str(args.get("tool_name") or args.get("name") or "").strip()
            tool_args = args.get("args") or args.get("arguments") or args.get("params") or {}
            target_server = str(args.get("server_name") or "").strip()

            if not target_tool:
                return "Error: 'tool_name' is required."

            if target_server and target_server in self._servers:
                return self._servers[target_server].call_tool(target_tool, tool_args)

            for s in self._servers.values():
                res = s.call_tool(target_tool, tool_args)
                if not str(res).startswith("MCP call error"):
                    return res
            return f"❌ Tool '{target_tool}' not found on any connected MCP server."

        # Support direct server tool calls like `myserver_mytool`
        for s_name, server in self._servers.items():
            prefix = f"{s_name.lower()}_"
            if tool_name.lower().startswith(prefix):
                real_name = tool_name[len(prefix):]
                return server.call_tool(real_name, args)

        return f"Unknown tool '{tool_name}' for MCP proxy connector."

    def health_check(self) -> bool:
        # MCP bridge itself is healthy; if servers are configured, also check if at least one is alive
        if not self._servers:
            return True
        return any(s.ping() for s in self._servers.values())
