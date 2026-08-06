# connectors/wikipedia.py — Wikipedia Connector (Zero-Setup, No Auth)
"""
Free Wikipedia connector. No API key, no setup required.
Uses the Wikipedia REST API v1 (public, no rate limit for reasonable use).
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Wikipedia")

_BASE = "https://en.wikipedia.org/api/rest_v1"
_SEARCH = "https://en.wikipedia.org/w/api.php"


class WikipediaConnector(BaseConnector):

    @property
    def connector_id(self) -> str:
        return "wikipedia"

    @property
    def display_name(self) -> str:
        return "Wikipedia"

    @property
    def description(self) -> str:
        return "Search and read Wikipedia articles instantly"

    @property
    def icon(self) -> str:
        return "📖"

    @property
    def requires_auth(self) -> bool:
        return False

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="search",
                description="Search Wikipedia for articles matching a query",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term"},
                        "limit": {"type": "integer", "description": "Max results (1-10)", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
            ConnectorTool(
                name="summary",
                description="Get a concise summary of a Wikipedia article",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Wikipedia article title"},
                    },
                    "required": ["title"],
                },
            ),
            ConnectorTool(
                name="full_article",
                description="Get the full text of a Wikipedia article (first 3000 chars)",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Wikipedia article title"},
                    },
                    "required": ["title"],
                },
            ),
        ]

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "search":
            return self._search(args.get("query", ""), int(args.get("limit", 5)))
        elif tool_name == "summary":
            return self._summary(args.get("title", ""))
        elif tool_name == "full_article":
            return self._full_article(args.get("title", ""))
        return f"Unknown tool: {tool_name}"

    def _fetch(self, url: str, timeout: float = 8.0) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-ConnectorHub/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _search(self, query: str, limit: int = 5) -> str:
        if not query.strip():
            return "Please provide a search query."
        params = urllib.parse.urlencode({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": min(limit, 10),
            "format": "json",
            "utf8": 1,
        })
        try:
            data = self._fetch(f"{_SEARCH}?{params}")
            results = data.get("query", {}).get("search", [])
            if not results:
                return f"No Wikipedia results found for '{query}'."
            lines = [f"📖 Wikipedia search results for **'{query}'**:\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                snippet = r.get("snippet", "").replace("<span class=\"searchmatch\">", "**").replace("</span>", "**")
                # Strip residual HTML
                import re
                snippet = re.sub(r"<[^>]+>", "", snippet)
                lines.append(f"{i}. **{title}**\n   {snippet}")
            return "\n".join(lines)
        except Exception as e:
            return f"Wikipedia search error: {e}"

    def _summary(self, title: str) -> str:
        if not title.strip():
            return "Please provide an article title."
        slug = urllib.parse.quote(title.replace(" ", "_"))
        try:
            data = self._fetch(f"{_BASE}/page/summary/{slug}")
            display_title = data.get("displaytitle", title)
            extract = data.get("extract", "No summary available.")
            url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            result = f"📖 **{display_title}**\n\n{extract}"
            if url:
                result += f"\n\n🔗 Read more: {url}"
            return result
        except Exception as e:
            return f"Wikipedia summary error for '{title}': {e}"

    def _full_article(self, title: str) -> str:
        if not title.strip():
            return "Please provide an article title."
        slug = urllib.parse.quote(title.replace(" ", "_"))
        try:
            data = self._fetch(f"{_BASE}/page/summary/{slug}")
            extract = data.get("extract", "")
            display_title = data.get("displaytitle", title)
            if not extract:
                return f"No content found for '{title}'."
            # Truncate to avoid token overflow
            truncated = extract[:3000]
            if len(extract) > 3000:
                truncated += "\n\n[...Article continues. Ask for specific sections.]"
            return f"📖 **{display_title}** (Wikipedia)\n\n{truncated}"
        except Exception as e:
            return f"Wikipedia article error for '{title}': {e}"

    def health_check(self) -> bool:
        try:
            self._fetch(f"{_BASE}/page/summary/Python_(programming_language)", timeout=5.0)
            return True
        except Exception:
            return False
