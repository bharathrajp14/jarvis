# tools/connector_tools.py — JARVIS Connector Hub Tool Registry Integration
"""
Registers the Connector Hub as callable JARVIS tools so the ReAct orchestrator
can invoke any connector directly from conversation.

Registered tools:
  - connector_status      → Show all connectors and their status
  - connector_call        → Call any connector tool by name
  - connector_search      → Smart search across all configured connectors
  - connector_add_mcp     → Dynamically add a new MCP server at runtime
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from .registry import register_tool

logger = logging.getLogger("JARVIS.ConnectorTools")


# ── Tool 1: Connector Status Dashboard ───────────────────────────────────────


@register_tool(
    name="connector_status",
    description=(
        "Show the status of all JARVIS connectors (Wikipedia, GitHub, Notion, Slack, "
        "Weather, YouTube, RSS News, Web Search, Filesystem, MCP servers and more). "
        "Use this to see which services are connected and what tools are available."
    ),
    parameters={"type": "object", "properties": {}},
)
def connector_status_action(args: Dict[str, Any]) -> str:
    """Display the Connector Hub status dashboard."""
    try:
        from brjarvis.connectors.hub import get_hub

        hub = get_hub()
        return hub.status_report()
    except Exception as e:
        return f"❌ Connector Hub error: {e}"


# ── Tool 2: Universal Connector Call ─────────────────────────────────────────


@register_tool(
    name="connector_call",
    description=(
        "Call a specific tool on a JARVIS connector plugin. "
        "Use connector_status first to see available connectors and their tools.\n"
        "Examples:\n"
        "  connector_id='wikipedia', tool_name='search', args={'query': 'neural networks'}\n"
        "  connector_id='github', tool_name='search_repos', args={'query': 'python AI'}\n"
        "  connector_id='weather', tool_name='current', args={'city': 'Chennai'}\n"
        "  connector_id='rss_news', tool_name='get_feed', args={'source': 'techcrunch'}\n"
        "  connector_id='slack', tool_name='get_messages', args={'channel': 'general'}\n"
        "  connector_id='notion', tool_name='search', args={'query': 'meeting notes'}\n"
        "  connector_id='filesystem', tool_name='list_files', args={'path': '.', 'pattern': '*.py'}\n"
        "  connector_id='youtube', tool_name='get_transcript', args={'video_id': 'dQw4w9WgXcQ'}"
    ),
    parameters={
        "type": "object",
        "properties": {
            "connector_id": {
                "type": "string",
                "description": "Connector identifier: wikipedia, github, weather, rss_news, slack, notion, youtube, web_search, filesystem, mcp_proxy",
            },
            "tool_name": {
                "type": "string",
                "description": "Tool name within the connector (e.g. 'search', 'get_feed', 'current')",
            },
            "args": {
                "type": "object",
                "description": "Tool-specific arguments dict",
            },
        },
        "required": ["connector_id", "tool_name"],
    },
)
def connector_call_action(args: Dict[str, Any]) -> str:
    """Route a call to a specific connector tool."""
    connector_id = str(args.get("connector_id", "")).strip()
    tool_name = str(args.get("tool_name", "")).strip()
    tool_args = args.get("args") or {}

    if not connector_id or not tool_name:
        return "❌ Both 'connector_id' and 'tool_name' are required."

    if not isinstance(tool_args, dict):
        try:
            tool_args = json.loads(str(tool_args))
        except Exception:
            tool_args = {}

    try:
        from brjarvis.connectors.hub import get_hub

        hub = get_hub()
        return hub.call(connector_id, tool_name, tool_args)
    except Exception as e:
        return f"❌ Connector call error: {e}"


# ── Tool 3: Smart Cross-Connector Search ─────────────────────────────────────


@register_tool(
    name="connector_search",
    description=(
        "Smart search that automatically queries the best available connectors for "
        "a given topic. Combines Wikipedia, Web Search, GitHub, and RSS news results "
        "in one call. Use this for broad research queries."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The topic or question to search across connectors",
            },
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific connector IDs to search (default: auto-selects best available)",
            },
        },
        "required": ["query"],
    },
)
def connector_search_action(args: Dict[str, Any]) -> str:
    """Search across multiple connectors simultaneously."""
    query = str(args.get("query", "")).strip()
    if not query:
        return "❌ Please provide a search query."

    requested_sources = args.get("sources", [])

    try:
        from brjarvis.connectors.hub import get_hub

        hub = get_hub()

        # Determine which connectors to search
        available = {c["id"] for c in hub.list_connectors() if c["configured"]}

        if requested_sources:
            search_sources = [s for s in requested_sources if s in available]
        else:
            # Default priority search order
            priority = ["web_search", "wikipedia", "rss_news", "github"]
            search_sources = [s for s in priority if s in available]

        if not search_sources:
            return "No configured connectors available for search. Run connector_status to see setup guide."

        results = []
        for source in search_sources[:4]:  # Limit to 4 sources
            try:
                result = hub.call(source, "search", {"query": query, "limit": 3})
                if result and "error" not in result.lower():
                    results.append(f"--- From **{source.replace('_', ' ').title()}** ---\n{result}")
            except Exception:
                # Try "instant_answer" or other fallback tools
                try:
                    connector = hub.get_connector(source)
                    if connector:
                        tools = [t.name for t in connector.list_tools()]
                        fallback = next((t for t in ["instant_answer", "get_feed", "search_repos"] if t in tools), None)
                        if fallback:
                            result = hub.call(source, fallback, {"query": query, "source": "hacker_news", "limit": 3})
                            if result:
                                results.append(f"--- From **{source.replace('_', ' ').title()}** ---\n{result}")
                except Exception as e:
                    logger.debug("Suppressed exception: %s", e)
        if not results:
            return f"No results found for '{query}' across connected sources."

        header = f"🔍 **Cross-Connector Search: '{query}'**\n\n"
        return header + "\n\n".join(results)

    except Exception as e:
        return f"❌ Cross-connector search error: {e}"


# ── Tool 4: Add MCP Server at Runtime ────────────────────────────────────────


@register_tool(
    name="connector_add_mcp",
    description=(
        "Dynamically connect JARVIS to a new MCP server at runtime. "
        "Works with any MCP-compatible server (local or remote). "
        "Popular local MCP servers: 'npx @modelcontextprotocol/server-filesystem', "
        "'npx @modelcontextprotocol/server-github', 'npx @modelcontextprotocol/server-sqlite'"
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "MCP server URL (e.g. http://localhost:3000)"},
            "name": {"type": "string", "description": "Friendly name for this server"},
            "api_key": {"type": "string", "description": "Optional API key for the server"},
        },
        "required": ["url"],
    },
)
def connector_add_mcp_action(args: Dict[str, Any]) -> str:
    """Dynamically add an MCP server to the connector hub."""
    url = str(args.get("url", "")).strip()
    name = str(args.get("name", "")).strip()
    api_key = str(args.get("api_key", "")).strip()

    if not url:
        return "❌ Please provide the MCP server URL."

    try:
        from brjarvis.connectors.hub import get_hub

        hub = get_hub()
        mcp_connector = hub.get_connector("mcp_proxy")
        if mcp_connector:
            return mcp_connector.add_server(url, name=name, api_key=api_key)
        return "❌ MCP proxy connector not loaded."
    except Exception as e:
        return f"❌ Failed to add MCP server: {e}"


# ── Tool 5: List Connector Tools ──────────────────────────────────────────────


@register_tool(
    name="connector_list_tools",
    description="List all available tools for a specific connector plugin.",
    parameters={
        "type": "object",
        "properties": {
            "connector_id": {
                "type": "string",
                "description": "Connector ID (e.g. 'github', 'notion', 'wikipedia')",
            },
        },
        "required": ["connector_id"],
    },
)
def connector_list_tools_action(args: Dict[str, Any]) -> str:
    """List tools for a specific connector."""
    connector_id = str(args.get("connector_id", "")).strip()
    if not connector_id:
        return "❌ Please provide a connector_id."

    try:
        from brjarvis.connectors.hub import get_hub

        hub = get_hub()
        connector = hub.get_connector(connector_id)
        if not connector:
            available = [c["id"] for c in hub.list_connectors()]
            return f"❌ Connector '{connector_id}' not found.\nAvailable: {available}"

        tools = connector.list_tools()
        lines = [f"{connector.icon} **{connector.display_name}** — Available Tools\n"]
        for t in tools:
            params = list((t.parameters.get("properties") or {}).keys())
            required = t.parameters.get("required", [])
            param_str = ", ".join(f"{p}{'*' if p in required else ''}" for p in params)
            lines.append(f"• **{t.name}**({param_str})\n  {t.description}")
        lines.append("\n*(Parameters marked with * are required)*")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ List tools error: {e}"
