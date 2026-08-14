# api/routes/connectors.py — Connector Hub Endpoints
from __future__ import annotations

import os
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("JARVIS.API.Connectors")
router = APIRouter(tags=["Connectors"])

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_API_FILE = _CONFIG_DIR / "api_keys.json"
_CONNECTORS_CACHE: dict | None = None
_CONNECTORS_CACHE_TS = 0.0
_CACHE_TTL_SECONDS = 5.0


def _read_full_config() -> dict:
    try:
        if _API_FILE.exists():
            return json.loads(_API_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


class ConnectorCallRequest(BaseModel):
    connector: str
    tool: str
    params: Dict[str, Any] = {}


class ConnectorConfigRequest(BaseModel):
    connector: str
    api_key: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


@router.get("/api/connectors")
async def get_connectors_list():
    """List registered App Connectors with real-time availability & auth status."""
    global _CONNECTORS_CACHE, _CONNECTORS_CACHE_TS
    now = time.time()
    if _CONNECTORS_CACHE is not None and (now - _CONNECTORS_CACHE_TS) < _CACHE_TTL_SECONDS:
        return _CONNECTORS_CACHE

    from tools.registry import TOOL_REGISTRY, _import_plugins
    _import_plugins()

    def _check_tools(tool_names: list[str], env_vars: list[str] | None = None) -> str:
        if env_vars and any(os.environ.get(v, "").strip() for v in env_vars):
            return "CONNECTED"
        return "CONNECTED" if any(t in TOOL_REGISTRY for t in tool_names) else "NOT_CONFIGURED"

    gmail_status = "NOT_CONFIGURED"
    gmail_desc = "Access inbox, list unread emails, send messages"
    try:
        from actions.gmail_auth import get_gmail_auth_manager
        g_st = get_gmail_auth_manager().get_status()
        if g_st.get("logged_in"):
            gmail_status = "CONNECTED"
            gmail_desc = f"Connected as {g_st.get('email')} ({g_st.get('auth_method')})"
        else:
            gmail_status = _check_tools(["gmail_login", "send_email"], ["GMAIL_APP_PASSWORD", "GOOGLE_CLIENT_ID"])
    except Exception:
        gmail_status = _check_tools(["gmail_login", "send_email"], ["GMAIL_APP_PASSWORD", "GOOGLE_CLIENT_ID"])

    contacts_count = 0
    try:
        from memory.contact_manager import get_contact_store
        contacts_count = get_contact_store().get_count()
    except Exception:
        pass

    connectors = [
        {"name": "Gmail / Google Account", "icon": "✉️", "status": gmail_status, "tools": ["gmail_login", "send_email"], "desc": gmail_desc},
        {"name": "Mobile Contacts Store", "icon": "📱", "status": "CONNECTED" if contacts_count > 0 else "NOT_CONFIGURED", "tools": ["import_contacts", "manage_contacts", "resolve_contact"], "desc": f"{contacts_count} saved contacts (.vcf/.csv import supported)"},
        {"name": "Notion Workspace", "icon": "📝", "status": _check_tools(["notion_search_pages", "notion_create_page"], ["NOTION_API_KEY", "NOTION_TOKEN"]), "tools": ["notion_search_pages", "notion_create_page"], "desc": "Search workspaces, create pages and notes"},
        {"name": "GitHub Developer", "icon": "🐙", "status": _check_tools(["github_list_prs", "github_create_issue"], ["GITHUB_TOKEN", "GH_TOKEN"]), "tools": ["github_list_prs", "github_create_issue"], "desc": "List pull requests, open issues and review code"},
        {"name": "Google Calendar", "icon": "📅", "status": _check_tools(["create_calendar_event", "list_calendar_events"], ["GOOGLE_CALENDAR_CREDENTIALS", "GOOGLE_CLIENT_ID"]), "tools": ["create_calendar_event", "list_calendar_events"], "desc": "Schedule meetings, inspect agenda and events"},
        {"name": "WhatsApp Automation", "icon": "💬", "status": _check_tools(["send_whatsapp", "manage_whatsapp_contacts"], ["WHATSAPP_TOKEN", "TWILIO_ACCOUNT_SID"]), "tools": ["send_whatsapp", "manage_whatsapp_contacts"], "desc": "Send instant & scheduled messages by contact name"},
        {"name": "Wikipedia Search", "icon": "🌐", "status": "CONNECTED", "tools": ["wikipedia_search"], "desc": "Live article summary & encyclopedia lookups"},
        {"name": "YouTube Search", "icon": "🎥", "status": "CONNECTED", "tools": ["youtube_search"], "desc": "Search videos, fetch transcripts & metadata"},
        {"name": "Weather Forecast", "icon": "🌤️", "status": _check_tools(["get_weather"], ["WEATHER_API_KEY", "OPENWEATHER_API_KEY"]), "tools": ["get_weather"], "desc": "Live temperature, humidity & multi-day forecast"},
        {"name": "RSS News Reader", "icon": "📰", "status": "CONNECTED", "tools": ["fetch_rss_news"], "desc": "Fetch top tech & global news headlines"},
        {"name": "Filesystem Explorer", "icon": "📂", "status": "CONNECTED", "tools": ["list_dir", "view_file"], "desc": "Inspect local directories & workspace files"},
        {"name": "MCP Proxy Connector", "icon": "🔌", "status": _check_tools(["mcp_call"], ["MCP_SERVER_URL"]), "tools": ["mcp_call"], "desc": "Model Context Protocol external server proxy"},
    ]
    payload = {"connectors": connectors}
    _CONNECTORS_CACHE = payload
    _CONNECTORS_CACHE_TS = now
    return payload


@router.get("/api/connector/status")
async def connector_status():
    """Return status of all registered connectors in the Connector Hub."""
    try:
        from connectors.hub import get_hub
        hub = get_hub()
        connectors = hub.list_connectors()
        return {
            "status": "ok",
            "count": len(connectors),
            "connectors": connectors,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "connectors": []}


@router.get("/api/connector/list")
async def connector_list():
    """Return all connectors and their available tools."""
    try:
        from connectors.hub import get_hub
        hub = get_hub()
        result = {}
        for c in hub.list_connectors():
            result[c["name"]] = {
                "icon": c.get("icon", "🔌"),
                "configured": c.get("configured", False),
                "tools": c.get("tools", []),
                "description": c.get("description", ""),
            }
        return {"status": "ok", "connectors": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/connector/call")
async def connector_call(req: ConnectorCallRequest):
    """Call a specific connector tool by connector name and tool name."""
    try:
        from connectors.hub import get_hub
        hub = get_hub()
        result = await asyncio.to_thread(hub.call, req.connector, req.tool, req.params)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/connector/config")
async def save_connector_config(req: ConnectorConfigRequest):
    """Save API key or configuration settings for a specific connector."""
    try:
        data = _read_full_config()
        conn_name = req.connector.lower().strip()
        key_name = f"{conn_name}_api_key"
        if req.api_key:
            val = req.api_key.strip()
            data[key_name] = val
            os.environ[key_name.upper()] = val
            if "github" in conn_name:
                os.environ["GITHUB_TOKEN"] = val
            elif "notion" in conn_name:
                os.environ["NOTION_API_KEY"] = val
            elif "weather" in conn_name:
                os.environ["OPENWEATHER_API_KEY"] = val
                os.environ["WEATHER_API_KEY"] = val
        if req.settings:
            data[f"{conn_name}_settings"] = req.settings

        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _API_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        logger.info("[ConnectorConfig] Saved configuration for '%s'", req.connector)
        return {"status": "ok", "message": f"Saved configuration for '{req.connector}'"}
    except Exception as e:
        logger.error("[ConnectorConfig] Error saving config: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
