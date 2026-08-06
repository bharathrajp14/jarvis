# connectors/rss_news.py — RSS/News Feed Connector (Zero-Setup, No Auth)
"""
RSS/Atom news feed reader connector.
Zero-setup, zero-auth. Works with any public RSS feed.
Pre-configured with popular free news sources.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.RSS")

# Pre-configured popular free RSS feeds
PRESET_FEEDS = {
    "bbc_world":       "http://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc_tech":        "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "techcrunch":      "https://techcrunch.com/feed/",
    "hacker_news":     "https://news.ycombinator.com/rss",
    "the_verge":       "https://www.theverge.com/rss/index.xml",
    "reuters":         "https://feeds.reuters.com/reuters/topNews",
    "wired":           "https://www.wired.com/feed/rss",
    "mit_tech_review": "https://www.technologyreview.com/feed/",
    "ai_news":         "https://aiweekly.co/issues.rss",
    "github_trending": "https://github-trending-api.fly.dev/feed",
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
                description=f"Read headlines from a preset news source or custom RSS URL. "
                            f"Preset sources: {', '.join(presets)}",
                parameters={
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": f"Preset name (e.g. 'bbc_tech', 'hacker_news') or full RSS URL",
                        },
                        "limit": {"type": "integer", "default": 10},
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
                            "description": "List of preset source names (defaults to top 3 news feeds)",
                        },
                    },
                    "required": ["keyword"],
                },
            ),
        ]

    def _fetch_rss(self, url: str) -> List[Dict]:
        """Fetch and parse an RSS/Atom feed. Returns list of article dicts."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JARVIS-ConnectorHub/1.0 RSS Reader"},
        )
        try:
            with urllib.request.urlopen(req, timeout=8.0) as r:
                content = r.read()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch feed: {e}")

        # Strip HTML entities that break XML parsing
        content_str = content.decode("utf-8", errors="replace")
        content_str = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[\da-fA-F]+;)([a-zA-Z]+);",
                             r"&amp;\1;", content_str)

        try:
            root = ET.fromstring(content_str)
        except ET.ParseError:
            # Try stripping namespaces as last resort
            content_str = re.sub(r' xmlns[^"]*"[^"]*"', "", content_str)
            root = ET.fromstring(content_str)

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        articles = []

        # RSS 2.0
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            # Strip HTML from description
            desc = re.sub(r"<[^>]+>", "", desc)[:200]
            if title:
                articles.append({"title": title, "url": link, "description": desc, "date": pub_date})

        # Atom feeds
        if not articles:
            for entry in root.findall(".//atom:entry", ns) or root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                summary_el = entry.find("{http://www.w3.org/2005/Atom}summary")
                updated_el = entry.find("{http://www.w3.org/2005/Atom}updated")
                title = (title_el.text or "").strip() if title_el is not None else ""
                link = link_el.get("href", "") if link_el is not None else ""
                desc = re.sub(r"<[^>]+>", "", (summary_el.text or ""))[:200] if summary_el is not None else ""
                date = (updated_el.text or "")[:10] if updated_el is not None else ""
                if title:
                    articles.append({"title": title, "url": link, "description": desc, "date": date})

        return articles

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "get_feed":
            return self._get_feed(args.get("source", ""), int(args.get("limit", 10)))
        elif tool_name == "list_sources":
            return self._list_sources()
        elif tool_name == "search_feeds":
            sources = args.get("sources", list(PRESET_FEEDS.keys())[:3])
            return self._search_feeds(args.get("keyword", ""), sources)
        return f"Unknown tool: {tool_name}"

    def _get_feed(self, source: str, limit: int = 10) -> str:
        url = PRESET_FEEDS.get(source, source)
        if not url.startswith("http"):
            return f"Unknown source '{source}'. Use list_sources to see available feeds or provide a full URL."
        try:
            articles = self._fetch_rss(url)[:limit]
            if not articles:
                return f"No articles found in feed: {url}"
            source_label = source if source in PRESET_FEEDS else url
            lines = [f"📰 **{source_label.replace('_', ' ').title()}** — Latest Headlines\n"]
            for a in articles:
                title = a["title"]
                link = a["url"]
                desc = a["description"]
                date = a["date"][:10] if a["date"] else ""
                date_str = f" ({date})" if date else ""
                desc_str = f"\n  {desc}" if desc else ""
                lines.append(f"• **{title}**{date_str}{desc_str}\n  🔗 {link}")
            return "\n".join(lines)
        except Exception as e:
            return f"RSS feed error for '{source}': {e}"

    def _list_sources(self) -> str:
        lines = ["📰 **Available News Feed Sources**\n"]
        for name, url in PRESET_FEEDS.items():
            lines.append(f"• **{name}** — {url}")
        lines.append("\nYou can also pass any full RSS URL directly as the 'source' parameter.")
        return "\n".join(lines)

    def _search_feeds(self, keyword: str, sources: List[str]) -> str:
        if not keyword:
            return "Please provide a keyword to search for."
        keyword_lower = keyword.lower()
        all_matches = []

        for source in sources[:5]:  # Limit to 5 sources max
            url = PRESET_FEEDS.get(source, source if source.startswith("http") else None)
            if not url:
                continue
            try:
                articles = self._fetch_rss(url)
                for a in articles:
                    if keyword_lower in a["title"].lower() or keyword_lower in a["description"].lower():
                        a["source"] = source
                        all_matches.append(a)
            except Exception:
                pass

        if not all_matches:
            return f"No articles found containing '{keyword}' across {len(sources)} feeds."

        lines = [f"📰 **News Search: '{keyword}'** ({len(all_matches)} matches)\n"]
        for a in all_matches[:10]:
            src = a.get("source", "unknown")
            lines.append(
                f"• **{a['title']}** [{src}]\n"
                f"  {a['description'][:150]}\n"
                f"  🔗 {a['url']}"
            )
        return "\n".join(lines)

    def health_check(self) -> bool:
        try:
            articles = self._fetch_rss(PRESET_FEEDS["hacker_news"])
            return len(articles) > 0
        except Exception:
            return False
