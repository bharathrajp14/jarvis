# connectors/notion.py — Notion Connector (Free Integration Token)
"""
Notion connector — read pages, search workspace, query databases.
Requires a free Notion Integration Token:
  notion.so → Settings → Connections → Develop or manage integrations
  Takes 3 minutes. No billing required.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Notion")

_API = "https://api.notion.com/v1"
_VERSION = "2022-06-28"


class NotionConnector(BaseConnector):

    def __init__(self):
        self._token = os.environ.get("NOTION_TOKEN", "").strip()

    @property
    def connector_id(self) -> str:
        return "notion"

    @property
    def display_name(self) -> str:
        return "Notion"

    @property
    def description(self) -> str:
        return "Search pages, read content, and query databases in your Notion workspace"

    @property
    def icon(self) -> str:
        return "📝"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    @property
    def auth_hint(self) -> str:
        return (
            "Add NOTION_TOKEN=secret_xxxx to your .env file.\n"
            "Get free token: notion.so → Settings → Connections → Develop integrations\n"
            "Then share the pages/databases with your integration."
        )

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="search",
                description="Search your Notion workspace for pages and databases",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="get_page",
                description="Read the content of a Notion page by its ID",
                parameters={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "Notion page ID or URL"},
                    },
                    "required": ["page_id"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="list_databases",
                description="List all databases accessible to your Notion integration",
                parameters={"type": "object", "properties": {}},
                requires_auth=True,
            ),
            ConnectorTool(
                name="query_database",
                description="Query records from a Notion database",
                parameters={
                    "type": "object",
                    "properties": {
                        "database_id": {"type": "string", "description": "Notion database ID"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["database_id"],
                },
                requires_auth=True,
            ),
        ]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": _VERSION,
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-ConnectorHub/1.0",
        }

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{_API}{path}", headers=self._headers())
        with urllib.request.urlopen(req, timeout=10.0) as r:
            return json.loads(r.read().decode())

    def _post(self, path: str, body: dict) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{_API}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10.0) as r:
            return json.loads(r.read().decode())

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "search":
            return self._search(args.get("query", ""), int(args.get("limit", 10)))
        elif tool_name == "get_page":
            return self._get_page(args.get("page_id", ""))
        elif tool_name == "list_databases":
            return self._list_databases()
        elif tool_name == "query_database":
            return self._query_database(args.get("database_id", ""), int(args.get("limit", 10)))
        return f"Unknown tool: {tool_name}"

    def _extract_page_id(self, page_id_or_url: str) -> str:
        """Extract clean page ID from URL or raw ID."""
        pid = page_id_or_url.strip()
        # Handle Notion URLs: .../Page-Title-abc123def456
        if "notion.so/" in pid:
            pid = pid.split("/")[-1]
            # Remove title portion before the UUID
            if "-" in pid:
                parts = pid.split("-")
                pid = parts[-1]
        # Strip dashes from UUID
        pid = pid.replace("-", "")
        if len(pid) == 32:
            # Insert dashes in UUID format
            pid = f"{pid[:8]}-{pid[8:12]}-{pid[12:16]}-{pid[16:20]}-{pid[20:]}"
        return pid

    def _extract_rich_text(self, rich_text_list: list) -> str:
        return "".join(rt.get("plain_text", "") for rt in (rich_text_list or []))

    def _search(self, query: str, limit: int = 10) -> str:
        try:
            body = {"query": query, "page_size": min(limit, 100)}
            data = self._post("/search", body)
            results = data.get("results", [])
            if not results:
                return f"No Notion content found for '{query}'."
            lines = [f"📝 **Notion Search: '{query}'**\n"]
            for item in results[:limit]:
                obj_type = item.get("object", "")
                item_id = item.get("id", "")
                if obj_type == "page":
                    props = item.get("properties", {})
                    title_prop = props.get("title") or props.get("Name") or {}
                    title_arr = title_prop.get("title", []) or title_prop.get("rich_text", [])
                    title = self._extract_rich_text(title_arr) or "Untitled"
                    url = item.get("url", "")
                    lines.append(f"• 📄 **{title}** (Page)\n  ID: `{item_id}`\n  🔗 {url}")
                elif obj_type == "database":
                    title_arr = item.get("title", [])
                    title = self._extract_rich_text(title_arr) or "Untitled Database"
                    url = item.get("url", "")
                    lines.append(f"• 🗄️ **{title}** (Database)\n  ID: `{item_id}`\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"Notion search error: {e}"

    def _get_page(self, page_id: str) -> str:
        try:
            pid = self._extract_page_id(page_id)
            page = self._get(f"/pages/{pid}")
            props = page.get("properties", {})
            title = "Untitled"
            for prop in props.values():
                prop_type = prop.get("type", "")
                if prop_type == "title":
                    title = self._extract_rich_text(prop.get("title", []))
                    break

            # Get page blocks (content)
            blocks_data = self._get(f"/blocks/{pid}/children")
            blocks = blocks_data.get("results", [])

            content_lines = []
            for block in blocks[:30]:  # Limit to first 30 blocks
                btype = block.get("type", "")
                bdata = block.get(btype, {})
                rich_text = bdata.get("rich_text", [])
                text = self._extract_rich_text(rich_text)
                if text:
                    if btype in ("heading_1", "heading_2", "heading_3"):
                        prefix = "#" * int(btype[-1])
                        content_lines.append(f"{prefix} {text}")
                    elif btype == "bulleted_list_item":
                        content_lines.append(f"• {text}")
                    elif btype == "numbered_list_item":
                        content_lines.append(f"1. {text}")
                    elif btype == "to_do":
                        checked = "✅" if bdata.get("checked") else "☐"
                        content_lines.append(f"{checked} {text}")
                    elif btype == "code":
                        lang = bdata.get("language", "")
                        content_lines.append(f"```{lang}\n{text}\n```")
                    else:
                        content_lines.append(text)

            url = page.get("url", "")
            content = "\n".join(content_lines) if content_lines else "(No text content)"
            if len(content) > 3000:
                content = content[:3000] + "\n\n[...Page continues. More blocks available.]"

            return f"📝 **{title}** (Notion Page)\n\n{content}\n\n🔗 {url}"
        except Exception as e:
            return f"Notion get_page error: {e}"

    def _list_databases(self) -> str:
        try:
            data = self._post("/search", {"filter": {"value": "database", "property": "object"}, "page_size": 20})
            dbs = data.get("results", [])
            if not dbs:
                return "No databases found. Make sure your integration is shared with your databases."
            lines = [f"📝 **Notion Databases** ({len(dbs)} found)\n"]
            for db in dbs:
                title = self._extract_rich_text(db.get("title", [])) or "Untitled"
                db_id = db.get("id", "")
                url = db.get("url", "")
                lines.append(f"• 🗄️ **{title}**\n  ID: `{db_id}`\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"Notion list databases error: {e}"

    def _query_database(self, database_id: str, limit: int = 10) -> str:
        try:
            did = self._extract_page_id(database_id)
            data = self._post(f"/databases/{did}/query", {"page_size": min(limit, 100)})
            results = data.get("results", [])
            if not results:
                return "No records found in this database."

            lines = [f"📝 **Notion Database Records** ({len(results)} rows)\n"]
            for page in results[:limit]:
                props = page.get("properties", {})
                row_parts = []
                for prop_name, prop_val in list(props.items())[:5]:
                    ptype = prop_val.get("type", "")
                    if ptype == "title":
                        val = self._extract_rich_text(prop_val.get("title", []))
                    elif ptype == "rich_text":
                        val = self._extract_rich_text(prop_val.get("rich_text", []))
                    elif ptype == "number":
                        val = str(prop_val.get("number", ""))
                    elif ptype == "select":
                        sel = prop_val.get("select")
                        val = sel.get("name", "") if sel else ""
                    elif ptype == "multi_select":
                        val = ", ".join(s["name"] for s in prop_val.get("multi_select", []))
                    elif ptype == "checkbox":
                        val = "✅" if prop_val.get("checkbox") else "☐"
                    elif ptype == "date":
                        date_obj = prop_val.get("date")
                        val = date_obj.get("start", "") if date_obj else ""
                    else:
                        val = ""
                    if val:
                        row_parts.append(f"{prop_name}: {val}")
                lines.append("• " + " | ".join(row_parts) if row_parts else "• (empty row)")
            return "\n".join(lines)
        except Exception as e:
            return f"Notion query database error: {e}"

    def health_check(self) -> bool:
        try:
            self._get("/users/me")
            return True
        except Exception:
            return False
