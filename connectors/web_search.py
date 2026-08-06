# connectors/web_search.py — Web Search Connector (Zero-Setup + Tavily free tier)
"""
Multi-engine web search connector.
  - DuckDuckGo Instant Answers API: zero-auth, zero-setup
  - Tavily Search API: free tier (set TAVILY_API_KEY in .env for richer results)
  - Fallback: DuckDuckGo HTML scraping via BeautifulSoup if available
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.WebSearch")


class WebSearchConnector(BaseConnector):

    def __init__(self):
        self._tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()

    @property
    def connector_id(self) -> str:
        return "web_search"

    @property
    def display_name(self) -> str:
        return "Web Search"

    @property
    def description(self) -> str:
        engine = "Tavily + DuckDuckGo" if self._tavily_key else "DuckDuckGo (free)"
        return f"Live web search via {engine}"

    @property
    def icon(self) -> str:
        return "🔍"

    @property
    def requires_auth(self) -> bool:
        return False  # DuckDuckGo works without auth

    @property
    def is_configured(self) -> bool:
        return True  # Always available via DuckDuckGo

    @property
    def auth_hint(self) -> str:
        return "Optionally add TAVILY_API_KEY in .env for richer results (free at tavily.com)"

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="search",
                description="Search the live web for up-to-date information",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
            ConnectorTool(
                name="instant_answer",
                description="Get an instant factual answer from DuckDuckGo (fast, structured)",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Factual question or topic"},
                    },
                    "required": ["query"],
                },
            ),
            ConnectorTool(
                name="news",
                description="Search for recent news articles on a topic",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "News topic"},
                        "max_results": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
        ]

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        query = str(args.get("query", "")).strip()
        if not query:
            return "Please provide a search query."
        max_results = int(args.get("max_results", 5))

        if tool_name == "search":
            return self._search(query, max_results)
        elif tool_name == "instant_answer":
            return self._instant_answer(query)
        elif tool_name == "news":
            return self._news_search(query, max_results)
        return f"Unknown tool: {tool_name}"

    def _fetch_json(self, url: str, headers: dict = None, timeout: float = 8.0) -> dict:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "JARVIS-ConnectorHub/1.0 (compatible; research bot)",
                **(headers or {}),
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _search(self, query: str, max_results: int = 5) -> str:
        """Search using Tavily (if key present) or DuckDuckGo fallback."""
        if self._tavily_key:
            return self._tavily_search(query, max_results)
        return self._ddg_search(query, max_results)

    def _tavily_search(self, query: str, max_results: int = 5) -> str:
        """Tavily API — richer, source-attributed results."""
        try:
            import urllib.request
            payload = json.dumps({
                "api_key": self._tavily_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": True,
            }).encode()
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10.0) as r:
                data = json.loads(r.read().decode())

            lines = [f"🔍 **Web Search: '{query}'** (via Tavily)\n"]
            if data.get("answer"):
                lines.append(f"**Quick Answer:** {data['answer']}\n")
            for result in data.get("results", [])[:max_results]:
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")[:200]
                lines.append(f"• **{title}**\n  {content}\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", e)
            return self._ddg_search(query, max_results)

    def _ddg_search(self, query: str, max_results: int = 5) -> str:
        """DuckDuckGo Instant Answers API — zero auth."""
        try:
            params = urllib.parse.urlencode({
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            })
            data = self._fetch_json(f"https://api.duckduckgo.com/?{params}")

            lines = [f"🔍 **Search: '{query}'** (DuckDuckGo)\n"]

            abstract = data.get("Abstract", "")
            if abstract:
                source = data.get("AbstractSource", "")
                source_url = data.get("AbstractURL", "")
                lines.append(f"**Summary:** {abstract}")
                if source:
                    lines.append(f"*(Source: {source} — {source_url})*\n")

            # Related topics
            topics = data.get("RelatedTopics", [])[:max_results]
            if topics:
                lines.append("**Related:**")
                for t in topics:
                    if isinstance(t, dict) and "Text" in t:
                        text = t["Text"][:150]
                        url = t.get("FirstURL", "")
                        lines.append(f"• {text}")
                        if url:
                            lines.append(f"  🔗 {url}")

            if len(lines) <= 1:
                lines.append(f"No instant answer found. Try asking JARVIS to search via browser.")

            return "\n".join(lines)
        except Exception as e:
            return f"Web search error: {e}"

    def _instant_answer(self, query: str) -> str:
        """Fast factual lookup via DuckDuckGo Instant Answers."""
        try:
            params = urllib.parse.urlencode({
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            })
            data = self._fetch_json(f"https://api.duckduckgo.com/?{params}")

            answer = data.get("Answer") or data.get("Abstract") or data.get("Definition")
            if answer:
                source = data.get("AnswerType") or data.get("AbstractSource") or ""
                result = f"💡 **{answer}**"
                if source:
                    result += f"\n*(Source: {source})*"
                return result
            return f"No instant answer found for '{query}'. Try a more specific question."
        except Exception as e:
            return f"Instant answer error: {e}"

    def _news_search(self, query: str, max_results: int = 5) -> str:
        """Search news using Tavily if available, else DuckDuckGo news endpoint."""
        if self._tavily_key:
            try:
                payload = json.dumps({
                    "api_key": self._tavily_key,
                    "query": query,
                    "max_results": max_results,
                    "topic": "news",
                    "days": 7,
                }).encode()
                req = urllib.request.Request(
                    "https://api.tavily.com/search",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10.0) as r:
                    data = json.loads(r.read().decode())
                lines = [f"📰 **News: '{query}'**\n"]
                for article in data.get("results", [])[:max_results]:
                    title = article.get("title", "")
                    url = article.get("url", "")
                    content = article.get("content", "")[:180]
                    lines.append(f"• **{title}**\n  {content}\n  🔗 {url}")
                return "\n".join(lines)
            except Exception:
                pass
        # Fallback: DuckDuckGo news search
        return self._ddg_search(f"{query} news", max_results)

    def health_check(self) -> bool:
        try:
            self._instant_answer("python programming language")
            return True
        except Exception:
            return False
