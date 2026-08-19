# connectors/rss_news.py — RSS/News Feed Connector (Zero-Setup, No Auth)
"""
RSS/Atom news feed reader connector.
Zero-setup, zero-auth. Works with any public RSS feed.
Pre-configured with popular free news sources.
"""

from __future__ import annotations

import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.RSS")

PRESET_FEEDS = {
    "bbc_world": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc_tech": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "techcrunch": "https://techcrunch.com/feed/",
    "hacker_news": "https://news.ycombinator.com/rss",
    "the_verge": "https://www.theverge.com/rss/index.xml",
    "reuters": "https://feeds.reuters.com/reuters/topNews",
    "wired": "https://www.wired.com/feed/rss",
    "mit_tech_review": "https://www.technologyreview.com/feed/",
    "ai_news": "https://aiweekly.co/issues.rss",
    "github_trending": "https://github-trending-api.fly.dev/feed",
}

PRESET_ALIASES = {
    "tech": "bbc_tech",
    "news": "bbc_world",
    "world": "bbc_world",
    "ai": "ai_news",
    "hackernews": "hacker_news",
    "verge": "the_verge",
    "mit": "mit_tech_review",
    "github": "github_trending",
}


class RSSNewsConnector(BaseConnector):
    @property
    def connector_id(self) -> str:
        return "rss_news"

    @property
    def display_name(self) -> str:
        return "RSS/News Feeds"

    @property
    def description(self) -> str:
        return "Read news from BBC, TechCrunch, HackerNews, Reuters, Wired + any RSS feed"

    @property
    def icon(self) -> str:
        return "📰"

    @property
    def requires_auth(self) -> bool:
        return False

    def list_tools(self) -> List[ConnectorTool]:
        presets = list(PRESET_FEEDS.keys())
        return [
            ConnectorTool(
                name="get_feed",
                description=f"Read headlines from a preset news source or custom RSS URL. Preset sources: {', '.join(presets)}",
                parameters={
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Preset name (e.g. 'bbc_tech', 'techcrunch', 'hacker_news') or full RSS URL",
                        },
                        "limit": {"type": "integer", "description": "Max articles (1-20)", "default": 10},
                    },
                    "required": ["source"],
                },
            ),
            ConnectorTool(
                name="list_sources",
                description="List all pre-configured news feed sources",
                parameters={"type": "object", "properties": {}},
            ),
            ConnectorTool(
                name="search_feeds",
                description="Search for articles containing a keyword across multiple news feeds",
                parameters={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Keyword to search for in article titles"},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of preset source names (defaults to top news feeds)",
                        },
                    },
                    "required": ["keyword"],
                },
            ),
        ]

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        norm_tool = tool_name.lower().replace("rss_", "").replace("get_", "")

        # Support tool named after a preset directly (e.g. 'tech', 'hacker_news')
        if norm_tool in PRESET_FEEDS or norm_tool in PRESET_ALIASES:
            source = PRESET_ALIASES.get(norm_tool, norm_tool)
            limit = int(args.get("limit") or 5)
            return self._get_feed(source, limit)

        if norm_tool in ("feed", "get_feed", "read", "headlines", "latest"):
            source = str(
                args.get("source")
                or args.get("category")
                or args.get("preset")
                or args.get("name")
                or args.get("url")
                or "bbc_tech"
            ).strip()
            limit = int(args.get("limit") or 10)
            return self._get_feed(source, limit)

        elif norm_tool in ("list_sources", "sources", "presets"):
            return self._list_sources()

        elif norm_tool in ("search_feeds", "search", "find"):
            keyword = str(args.get("keyword") or args.get("query") or "").strip()
            sources = args.get("sources") or ["bbc_tech", "techcrunch", "hacker_news", "the_verge"]
            return self._search_feeds(keyword, sources)

        return f"Unknown tool: {tool_name}"

    def _fetch_rss(self, url: str) -> List[Dict]:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JARVIS-ConnectorHub/1.0 (RSS Reader; +https://github.com/bharthraj1412/BrJarvis)"},
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            content = resp.read()

        root = ET.fromstring(content)
        items = []

        # RSS 2.0: channel/item
        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub = item.findtext("pubDate", "").strip()
            desc_clean = re.sub(r"<[^>]+>", "", desc)[:200].strip()
            if title:
                items.append({"title": title, "link": link, "summary": desc_clean, "published": pub})

        # Atom: feed/entry
        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
                title = entry.findtext("{http://www.w3.org/2005/Atom}title", "").strip()
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.get("href", "") if link_el is not None else ""
                summary = entry.findtext("{http://www.w3.org/2005/Atom}summary", "") or entry.findtext(
                    "{http://www.w3.org/2005/Atom}content", ""
                )
                summary_clean = re.sub(r"<[^>]+>", "", summary)[:200].strip()
                if title:
                    items.append({"title": title, "link": link, "summary": summary_clean, "published": ""})

        return items

    def _get_feed(self, source: str, limit: int = 10) -> str:
        resolved_source = PRESET_ALIASES.get(source.lower(), source)
        url = PRESET_FEEDS.get(resolved_source, source)
        label = resolved_source if resolved_source in PRESET_FEEDS else url

        try:
            items = self._fetch_rss(url)
            if not items:
                return f"📰 No articles found in feed: {label}"

            lines = [f"📰 **{label.upper()} — Top Headlines ({min(limit, len(items))} articles):**\n"]
            for i, item in enumerate(items[:limit], 1):
                lines.append(f"{i}. **{item['title']}**")
                if item["summary"]:
                    lines.append(f"   {item['summary']}")
                if item["link"]:
                    lines.append(f"   🔗 {item['link']}")
                lines.append("")
            return "\n".join(lines).strip()
        except Exception as e:
            return f"Failed to fetch RSS feed '{label}': {e}"

    def _list_sources(self) -> str:
        lines = ["📰 **Pre-Configured News Feeds (Zero Auth):**\n"]
        for name, url in PRESET_FEEDS.items():
            lines.append(f"• `{name}` — {url}")
        lines.append("\n*You can also pass any full custom RSS/Atom URL.*")
        return "\n".join(lines)

    def _search_feeds(self, keyword: str, sources: List[str]) -> str:
        if not keyword:
            return "Please provide a keyword to search for."
        matches = []
        kw_lower = keyword.lower()

        for src in sources:
            resolved_src = PRESET_ALIASES.get(src.lower(), src)
            url = PRESET_FEEDS.get(resolved_src, src)
            try:
                items = self._fetch_rss(url)
                for item in items:
                    if kw_lower in item["title"].lower() or kw_lower in item["summary"].lower():
                        matches.append({"source": resolved_src, **item})
            except Exception:
                continue

        if not matches:
            return f"📰 No articles found matching '{keyword}' across sources."

        lines = [f"📰 **News Search Results for '{keyword}' ({len(matches[:10])} matches):**\n"]
        for m in matches[:10]:
            lines.append(f"• [{m['source']}] **{m['title']}**")
            if m["summary"]:
                lines.append(f"  {m['summary']}")
            if m["link"]:
                lines.append(f"  🔗 {m['link']}")
        return "\n".join(lines)

    def health_check(self) -> bool:
        try:
            items = self._fetch_rss(PRESET_FEEDS["bbc_tech"])
            return len(items) > 0
        except Exception:
            return False
