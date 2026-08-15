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
                description="Get a concise summary of a Wikipedia article or topic",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Wikipedia article title or topic query"},
                        "sentences": {"type": "integer", "description": "Number of sentences to return", "default": 3},
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
        norm_tool = tool_name.lower().replace("wikipedia_", "").replace("wiki_", "")

        topic = str(
            args.get("title")
            or args.get("query")
            or args.get("topic")
            or args.get("article")
            or args.get("q")
            or ""
        ).strip()

        if norm_tool in ("search", "find", "lookup"):
            limit = int(args.get("limit") or 5)
            return self._search(topic, limit)
        elif norm_tool in ("summary", "get_summary", "quick", "describe"):
            sentences = int(args.get("sentences") or 3)
            return self._summary(topic, sentences)
        elif norm_tool in ("full_article", "full", "article", "read"):
            return self._full_article(topic)
        return f"Unknown tool: {tool_name}"

    def _fetch(self, url: str, timeout: float = 8.0) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-ConnectorHub/1.0 (research assistant)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _search(self, query: str, limit: int = 5) -> str:
        if not query.strip():
            return "Please provide a search query."
        try:
            params = urllib.parse.urlencode({
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": min(limit, 10),
            })
            data = self._fetch(f"{_SEARCH}?{params}")
            results = data.get("query", {}).get("search", [])
            if not results:
                return f"📖 No Wikipedia articles found for '{query}'."

            lines = [f"📖 **Wikipedia Search: '{query}'**\n"]
            for r in results:
                title = r.get("title", "")
                snippet = r.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                lines.append(f"• **{title}**\n  {snippet}...\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"Wikipedia search error: {e}"

    def _summary(self, title: str, sentences: int = 3) -> str:
        if not title.strip():
            return "Please provide an article title or topic."
        try:
            safe_title = urllib.parse.quote(title.strip().replace(" ", "_"))
            try:
                data = self._fetch(f"{_BASE}/page/summary/{safe_title}")
            except Exception:
                # If exact title failed, search for top title
                params = urllib.parse.urlencode({
                    "action": "query",
                    "list": "search",
                    "srsearch": title,
                    "format": "json",
                    "srlimit": 1,
                })
                s_data = self._fetch(f"{_SEARCH}?{params}")
                results = s_data.get("query", {}).get("search", [])
                if not results:
                    return f"📖 No Wikipedia article found for '{title}'."
                top_title = results[0]["title"]
                safe_title = urllib.parse.quote(top_title.replace(" ", "_"))
                data = self._fetch(f"{_BASE}/page/summary/{safe_title}")

            display_title = data.get("title", title)
            extract = data.get("extract", "")
            if not extract:
                return f"📖 No summary available for '{display_title}'."

            # Trim by sentence count if needed
            s_list = extract.split(". ")
            if len(s_list) > sentences:
                extract = ". ".join(s_list[:sentences]) + "."

            url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            description = data.get("description", "")
            desc_line = f"*{description}*\n" if description else ""

            return f"📖 **{display_title}**\n{desc_line}\n{extract}\n\n🔗 {url}"
        except Exception as e:
            return f"Wikipedia summary error for '{title}': {e}"

    def _full_article(self, title: str) -> str:
        if not title.strip():
            return "Please provide an article title."
        try:
            safe_title = urllib.parse.quote(title.strip().replace(" ", "_"))
            params = urllib.parse.urlencode({
                "action": "query",
                "prop": "extracts",
                "titles": title,
                "explaintext": 1,
                "exlimit": 1,
                "format": "json",
            })
            data = self._fetch(f"{_SEARCH}?{params}")
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if pid == "-1":
                    return f"📖 Article '{title}' not found on Wikipedia."
                extract = page.get("extract", "")
                trimmed = extract[:3000]
                if len(extract) > 3000:
                    trimmed += f"\n\n*[... Article truncated. Full length: {len(extract)} characters]*"
                url = f"https://en.wikipedia.org/wiki/{safe_title}"
                return f"📖 **{page.get('title', title)}** (Full Text)\n\n{trimmed}\n\n🔗 {url}"
            return f"📖 Article '{title}' not found on Wikipedia."
        except Exception as e:
            return f"Wikipedia full article error: {e}"

    def health_check(self) -> bool:
        try:
            self._fetch(f"{_BASE}/page/summary/Python_(programming_language)")
            return True
        except Exception:
            return False
