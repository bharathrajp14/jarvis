# connectors/youtube.py — YouTube Connector (Free API Key)
"""
YouTube connector — search videos, get channel info, fetch transcripts.
Requires a free YouTube Data API v3 key:
  console.cloud.google.com → Enable YouTube Data API v3 → Create API Key
  Free quota: 10,000 units/day (sufficient for normal use)
  Takes 5 minutes.

Bonus: Video transcript fetching works WITHOUT any API key (using youtube-transcript-api).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.YouTube")

_API = "https://www.googleapis.com/youtube/v3"


class YouTubeConnector(BaseConnector):

    def __init__(self):
        self._api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()

    @property
    def connector_id(self) -> str:
        return "youtube"

    @property
    def display_name(self) -> str:
        return "YouTube"

    @property
    def description(self) -> str:
        return "Search YouTube videos, get channel info, and fetch video transcripts"

    @property
    def icon(self) -> str:
        return "▶️"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_configured(self) -> bool:
        # Transcript tool works even without API key
        return True

    @property
    def auth_hint(self) -> str:
        return (
            "For full search: add YOUTUBE_API_KEY=AIzaXXXX to your .env file.\n"
            "Get free key: console.cloud.google.com → YouTube Data API v3\n"
            "Note: video transcript fetching works WITHOUT any key (run: pip install youtube-transcript-api)"
        )

    def list_tools(self) -> List[ConnectorTool]:
        tools = [
            ConnectorTool(
                name="get_transcript",
                description="Get the full transcript/subtitles of a YouTube video (no API key needed)",
                parameters={
                    "type": "object",
                    "properties": {
                        "video_id": {
                            "type": "string",
                            "description": "YouTube video ID or full URL (e.g. 'dQw4w9WgXcQ' or 'https://youtube.com/watch?v=dQw4w9WgXcQ')",
                        },
                        "language": {"type": "string", "description": "Language code (e.g. 'en', 'hi')", "default": "en"},
                    },
                    "required": ["video_id"],
                },
            ),
        ]
        if self._api_key:
            tools = [
                ConnectorTool(
                    name="search",
                    description="Search YouTube for videos by keyword",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "integer", "default": 5},
                            "order": {"type": "string", "enum": ["relevance", "date", "viewCount"], "default": "relevance"},
                        },
                        "required": ["query"],
                    },
                    requires_auth=True,
                ),
                ConnectorTool(
                    name="get_video_details",
                    description="Get detailed metadata for a YouTube video",
                    parameters={
                        "type": "object",
                        "properties": {
                            "video_id": {"type": "string", "description": "YouTube video ID"},
                        },
                        "required": ["video_id"],
                    },
                    requires_auth=True,
                ),
                ConnectorTool(
                    name="get_channel",
                    description="Get information about a YouTube channel",
                    parameters={
                        "type": "object",
                        "properties": {
                            "channel_id": {"type": "string", "description": "Channel ID or handle (e.g. '@MrBeast')"},
                        },
                        "required": ["channel_id"],
                    },
                    requires_auth=True,
                ),
            ] + tools

        return tools

    def _extract_video_id(self, video_id_or_url: str) -> str:
        """Extract video ID from URL or return as-is if it's already an ID."""
        vid = video_id_or_url.strip()
        if "youtube.com/watch" in vid:
            parsed = urllib.parse.urlparse(vid)
            return urllib.parse.parse_qs(parsed.query).get("v", [vid])[0]
        elif "youtu.be/" in vid:
            return vid.split("youtu.be/")[-1].split("?")[0]
        return vid

    def _fetch(self, endpoint: str, params: dict) -> dict:
        params["key"] = self._api_key
        url = f"{_API}/{endpoint}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-ConnectorHub/1.0"})
        with urllib.request.urlopen(req, timeout=10.0) as r:
            return json.loads(r.read().decode())

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "search":
            return self._search(args.get("query", ""), int(args.get("max_results", 5)), args.get("order", "relevance"))
        elif tool_name == "get_video_details":
            return self._get_video_details(self._extract_video_id(args.get("video_id", "")))
        elif tool_name == "get_channel":
            return self._get_channel(args.get("channel_id", ""))
        elif tool_name == "get_transcript":
            vid_id = self._extract_video_id(args.get("video_id", ""))
            return self._get_transcript(vid_id, args.get("language", "en"))
        return f"Unknown tool: {tool_name}"

    def _search(self, query: str, max_results: int = 5, order: str = "relevance") -> str:
        if not self._api_key:
            return "YouTube search requires YOUTUBE_API_KEY in .env. Video transcript fetching works without it."
        try:
            data = self._fetch("search", {
                "part": "snippet",
                "q": query,
                "maxResults": min(max_results, 10),
                "type": "video",
                "order": order,
            })
            items = data.get("items", [])
            if not items:
                return f"No YouTube videos found for '{query}'."
            lines = [f"▶️ **YouTube Search: '{query}'**\n"]
            for item in items:
                vid_id = item["id"].get("videoId", "")
                snippet = item.get("snippet", {})
                title = snippet.get("title", "")
                channel = snippet.get("channelTitle", "")
                desc = snippet.get("description", "")[:120]
                url = f"https://youtube.com/watch?v={vid_id}"
                lines.append(f"• **{title}**\n  Channel: {channel}\n  {desc}\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"YouTube search error: {e}"

    def _get_video_details(self, video_id: str) -> str:
        if not self._api_key:
            return "Video details require YOUTUBE_API_KEY in .env."
        try:
            data = self._fetch("videos", {
                "part": "snippet,statistics,contentDetails",
                "id": video_id,
            })
            items = data.get("items", [])
            if not items:
                return f"Video '{video_id}' not found."
            v = items[0]
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            description = snippet.get("description", "")[:300]
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            duration = v.get("contentDetails", {}).get("duration", "").replace("PT", "").lower()
            url = f"https://youtube.com/watch?v={video_id}"
            return (
                f"▶️ **{title}**\n"
                f"• Channel: {channel}\n"
                f"• Duration: {duration}\n"
                f"• Views: {views:,} | Likes: {likes:,} | Comments: {comments:,}\n"
                f"• Description: {description}\n"
                f"🔗 {url}"
            )
        except Exception as e:
            return f"YouTube video details error: {e}"

    def _get_channel(self, channel_id: str) -> str:
        if not self._api_key:
            return "Channel info requires YOUTUBE_API_KEY in .env."
        try:
            # Handle @handle format
            params = {
                "part": "snippet,statistics",
                "maxResults": 1,
            }
            if channel_id.startswith("@"):
                params["forHandle"] = channel_id[1:]
            elif channel_id.startswith("UC"):
                params["id"] = channel_id
            else:
                params["forHandle"] = channel_id.lstrip("@")

            data = self._fetch("channels", params)
            items = data.get("items", [])
            if not items:
                return f"Channel '{channel_id}' not found."
            ch = items[0]
            snippet = ch.get("snippet", {})
            stats = ch.get("statistics", {})
            name = snippet.get("title", "")
            desc = snippet.get("description", "")[:250]
            subscribers = int(stats.get("subscriberCount", 0))
            videos = int(stats.get("videoCount", 0))
            views = int(stats.get("viewCount", 0))
            cid = ch.get("id", "")
            return (
                f"▶️ **{name}** (YouTube Channel)\n"
                f"• Subscribers: {subscribers:,}\n"
                f"• Total Videos: {videos:,}\n"
                f"• Total Views: {views:,}\n"
                f"• Description: {desc}\n"
                f"🔗 https://youtube.com/channel/{cid}"
            )
        except Exception as e:
            return f"YouTube channel error: {e}"

    def _get_transcript(self, video_id: str, language: str = "en") -> str:
        """Fetch video transcript using youtube-transcript-api (no API key needed)."""
        if not video_id:
            return "Please provide a video ID or URL."
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
            transcripts = YouTubeTranscriptApi.get_transcript(video_id, languages=[language, "en"])
            full_text = " ".join(t["text"] for t in transcripts)
            if len(full_text) > 5000:
                full_text = full_text[:5000] + "\n\n[...Transcript continues. Truncated at 5000 chars.]"
            url = f"https://youtube.com/watch?v={video_id}"
            return f"▶️ **YouTube Transcript** — {url}\n\n{full_text}"
        except ImportError:
            return (
                "youtube-transcript-api not installed.\n"
                "Run: pip install youtube-transcript-api\n"
                "Then try again — this tool requires no API key."
            )
        except Exception as e:
            return f"Transcript error for '{video_id}': {e}\n(Video may not have subtitles available)"

    def health_check(self) -> bool:
        # Transcript tool always works; search needs API key
        return True
