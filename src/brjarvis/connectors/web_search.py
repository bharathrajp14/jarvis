# connectors/web_search.py — Web Search Connector (Zero-Setup + Tavily AI Search Engine)
"""
Multi-engine web search connector.
  - Tavily Search API: AI-optimized live search & content extraction (uses TAVILY_API_KEY from .env)
  - DuckDuckGo Instant Answers & search: zero-auth, zero-setup fallback
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.WebSearch")


class WebSearchConnector(BaseConnector):
    @property
    def _tavily_key(self) -> str:
        return os.environ.get("TAVILY_API_KEY", "").strip()

    @property
    def connector_id(self) -> str:
        return "web_search"

    @property
    def display_name(self) -> str:
        return "Web Search"

    @property
    def description(self) -> str:
        engine = "Tavily AI Engine" if self._tavily_key else "DuckDuckGo (free)"
        return f"Live web search, news retrieval & page extraction via {engine}"

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
        return "Optionally add TAVILY_API_KEY in .env for richer AI results (free at tavily.com)"

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="search",
                description="Search the live web for up-to-date information, news, and technical solutions",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query or question"},
                        "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5},
                        "search_depth": {"type": "string", "enum": ["basic", "advanced"], "default": "advanced"},
                    },
                    "required": ["query"],
                },
            ),
            ConnectorTool(
                name="extract",
                description="Extract full clean text and content from one or more target web URLs",
                parameters={
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of URLs to extract content from",
                        },
                        "url": {"type": "string", "description": "Single URL to extract content from"},
                    },
                },
            ),
            ConnectorTool(
                name="instant_answer",
                description="Get an instant factual answer from DuckDuckGo or Tavily Q&A",
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
                description="Search for recent news articles on a specific topic",
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
        if tool_name == "extract":
            urls = args.get("urls") or ([args["url"]] if args.get("url") else [])
            return self._extract_urls(urls)

        query = str(args.get("query") or args.get("q") or "").strip()
        if not query:
            return "Please provide a search query."
        max_results = int(args.get("max_results") or args.get("limit") or 5)
        depth = str(args.get("search_depth", "advanced"))

        if tool_name in ("search", "web_search", "query"):
            return self._search(query, max_results, depth)
        elif tool_name in ("instant_answer", "answer", "fact"):
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
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _search(self, query: str, max_results: int = 5, depth: str = "advanced") -> str:
        """Search using Tavily (if key present) or DuckDuckGo fallback."""
        if self._tavily_key:
            return self._tavily_search(query, max_results, depth)
        return self._ddg_search(query, max_results)

    def _tavily_search(self, query: str, max_results: int = 5, depth: str = "advanced") -> str:
        """Tavily API — richer, source-attributed results."""
        try:
            payload = json.dumps(
                {
                    "api_key": self._tavily_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": depth,
                    "include_answer": True,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12.0) as r:
                data = json.loads(r.read().decode("utf-8"))

            lines = [f"🔍 **Web Search: '{query}'** (via Tavily)\n"]
            if data.get("answer"):
                lines.append(f"**Quick Answer:** {data['answer']}\n")
            for result in data.get("results", [])[:max_results]:
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")[:280]
                lines.append(f"• **{title}**\n  {content}\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", e)
            return self._ddg_search(query, max_results)

    def _extract_urls(self, urls: List[str]) -> str:
        """Extract full-text content from URLs using Tavily Extract API."""
        if not urls:
            return "Please provide at least one URL to extract."

        if self._tavily_key:
            try:
                payload = json.dumps(
                    {
                        "api_key": self._tavily_key,
                        "urls": urls[:5],
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.tavily.com/extract",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15.0) as r:
                    data = json.loads(r.read().decode("utf-8"))

                lines = ["📄 **Tavily URL Extraction Results:**\n"]
                for item in data.get("results", []):
                    u = item.get("url", "")
                    content = item.get("raw_content", "")[:1200]
                    lines.append(f"• **URL**: {u}\n```\n{content}\n```")
                return "\n".join(lines)
            except Exception as e:
                logger.warning("Tavily extract failed: %s", e)

        # Fallback basic text scrape
        lines = ["📄 **URL Content Extraction:**\n"]
        for u in urls[:3]:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    clean = " ".join(raw.split())[:800]
                    lines.append(f"• **URL**: {u}\n```\n{clean}\n```")
            except Exception as ex:
                lines.append(f"• **URL**: {u} (Error: {ex})")
        return "\n".join(lines)

    def _ddg_search(self, query: str, max_results: int = 5) -> str:
        """DuckDuckGo Instant Answers API — zero auth."""
        try:
            params = urllib.parse.urlencode(
                {
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                }
            )
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
                lines.append("**Related Results:**")
                for t in topics:
                    if isinstance(t, dict) and "Text" in t:
                        text = t["Text"][:180]
                        url = t.get("FirstURL", "")
                        lines.append(f"• {text}\n  🔗 {url}")

            if len(lines) <= 1:
                lines.append(f"No instant answer found for '{query}'.")

            return "\n".join(lines)
        except Exception as e:
            return f"Web search error: {e}"

    def _instant_answer(self, query: str) -> str:
        """Fast factual lookup."""
        if self._tavily_key:
            res = self._tavily_search(query, max_results=1, depth="basic")
            if "Quick Answer:" in res:
                return res

        try:
            params = urllib.parse.urlencode(
                {
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                }
            )
            data = self._fetch_json(f"https://api.duckduckgo.com/?{params}")

            answer = data.get("Answer") or data.get("Abstract") or data.get("Definition")
            if answer:
                source = data.get("AnswerType") or data.get("AbstractSource") or ""
                result = f"💡 **{answer}**"
                if source:
                    result += f"\n*(Source: {source})*"
                return result
            return f"No instant answer found for '{query}'."
        except Exception as e:
            return f"Instant answer error: {e}"

    def _news_search(self, query: str, max_results: int = 5) -> str:
        """Search news using Tavily if available, else DuckDuckGo news endpoint."""
        if self._tavily_key:
            try:
                payload = json.dumps(
                    {
                        "api_key": self._tavily_key,
                        "query": query,
                        "max_results": max_results,
                        "topic": "news",
                        "days": 7,
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.tavily.com/search",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10.0) as r:
                    data = json.loads(r.read().decode("utf-8"))
                lines = [f"📰 **News: '{query}'** (via Tavily)\n"]
                for article in data.get("results", [])[:max_results]:
                    title = article.get("title", "")
                    url = article.get("url", "")
                    content = article.get("content", "")[:200]
                    lines.append(f"• **{title}**\n  {content}\n  🔗 {url}")
                return "\n".join(lines)
            except Exception:
                pass
        return self._ddg_search(f"{query} news", max_results)

    def health_check(self) -> bool:
        try:
            self._instant_answer("python programming language")
            return True
        except Exception:
            return False


def search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Standalone search helper for stage decomposer and agent workflows."""
    connector = WebSearchConnector()
    raw = connector._ddg_search(query, max_results=max_results)
    return [{"title": f"Web Search Result: {query}", "snippet": raw, "url": ""}]
