# connectors/slack.py — Slack Connector (Free Bot Token)
"""
Slack connector — read messages, search workspace, post messages.
Requires a free Slack Bot Token (no paid plan needed):
  api.slack.com → Create App → Add to Workspace → OAuth & Permissions
  Scopes: channels:read, channels:history, search:read, chat:write
  Takes 5 minutes. Works on free Slack workspaces.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Slack")

_API = "https://slack.com/api"


class SlackConnector(BaseConnector):
    def __init__(self):
        self._token = os.environ.get("SLACK_BOT_TOKEN", "").strip()

    @property
    def connector_id(self) -> str:
        return "slack"

    @property
    def display_name(self) -> str:
        return "Slack"

    @property
    def description(self) -> str:
        return "Read channels, search messages, and post to Slack workspaces"

    @property
    def icon(self) -> str:
        return "💬"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    @property
    def auth_hint(self) -> str:
        return (
            "Add SLACK_BOT_TOKEN=xoxb-xxxx to your .env file.\n"
            "Get free token: api.slack.com → Create App → Install to Workspace\n"
            "Required scopes: channels:read, channels:history, search:read, chat:write"
        )

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="list_channels",
                description="List all channels in your Slack workspace",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="get_messages",
                description="Read recent messages from a Slack channel",
                parameters={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel name (e.g. 'general') or ID"},
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["channel"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="search_messages",
                description="Search for messages across your Slack workspace",
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
                name="send_message",
                description="Send a message to a Slack channel",
                parameters={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel name or ID"},
                        "message": {"type": "string", "description": "Message text to send"},
                    },
                    "required": ["channel", "message"],
                },
                requires_auth=True,
            ),
        ]

    def _call_api(self, method: str, params: dict = None, post_data: dict = None) -> dict:
        if post_data:
            data = json.dumps(post_data).encode()
            req = urllib.request.Request(
                f"{_API}/{method}",
                data=data,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                    "User-Agent": "JARVIS-ConnectorHub/1.0",
                },
                method="POST",
            )
        else:
            url = f"{_API}/{method}"
            if params:
                url += "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "User-Agent": "JARVIS-ConnectorHub/1.0",
                },
            )
        with urllib.request.urlopen(req, timeout=10.0) as r:
            return json.loads(r.read().decode())

    def _resolve_channel_id(self, channel: str) -> str:
        """Resolve channel name to ID if needed."""
        if channel.startswith("C") and len(channel) >= 9:
            return channel  # Already an ID
        name = channel.lstrip("#").lower()
        try:
            data = self._call_api("conversations.list", {"limit": 200, "types": "public_channel,private_channel"})
            for ch in data.get("channels", []):
                if ch.get("name", "").lower() == name:
                    return ch["id"]
        except Exception as e:
            logger.debug("Suppressed exception: %s", e)
        return channel  # Return as-is and let Slack handle it

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "list_channels":
            return self._list_channels(int(args.get("limit", 20)))
        elif tool_name == "get_messages":
            return self._get_messages(args.get("channel", ""), int(args.get("limit", 20)))
        elif tool_name == "search_messages":
            return self._search_messages(args.get("query", ""), int(args.get("limit", 10)))
        elif tool_name == "send_message":
            return self._send_message(args.get("channel", ""), args.get("message", ""))
        return f"Unknown tool: {tool_name}"

    def _list_channels(self, limit: int = 20) -> str:
        try:
            data = self._call_api(
                "conversations.list",
                {
                    "limit": min(limit, 200),
                    "types": "public_channel,private_channel",
                    "exclude_archived": True,
                },
            )
            if not data.get("ok"):
                return f"Slack error: {data.get('error', 'unknown')}"
            channels = data.get("channels", [])
            if not channels:
                return "No channels found."
            lines = [f"💬 **Slack Channels** ({len(channels)} found)\n"]
            for ch in channels[:limit]:
                name = ch.get("name", "")
                members = ch.get("num_members", 0)
                topic = ch.get("topic", {}).get("value", "")
                purpose = ch.get("purpose", {}).get("value", "")
                desc = topic or purpose or ""
                desc_str = f" — {desc[:80]}" if desc else ""
                lines.append(f"• **#{name}** ({members} members){desc_str}")
            return "\n".join(lines)
        except Exception as e:
            return f"Slack list channels error: {e}"

    def _get_messages(self, channel: str, limit: int = 20) -> str:
        try:
            ch_id = self._resolve_channel_id(channel)
            data = self._call_api("conversations.history", {"channel": ch_id, "limit": min(limit, 100)})
            if not data.get("ok"):
                return f"Slack error: {data.get('error', 'unknown')}\nMake sure the bot is added to #{channel}"
            messages = data.get("messages", [])
            if not messages:
                return f"No messages found in #{channel}."
            lines = [f"💬 **#{channel} — Recent Messages**\n"]
            for msg in reversed(messages[:limit]):  # Show oldest first
                user = msg.get("user", msg.get("username", "unknown"))
                text = msg.get("text", "")
                ts = msg.get("ts", "")
                # Convert timestamp to readable time
                if ts:
                    import datetime

                    dt = datetime.datetime.fromtimestamp(float(ts))
                    time_str = dt.strftime("%H:%M")
                else:
                    time_str = ""
                if text:
                    lines.append(f"• [{time_str}] @{user}: {text[:200]}")
            return "\n".join(lines)
        except Exception as e:
            return f"Slack get messages error: {e}"

    def _search_messages(self, query: str, limit: int = 10) -> str:
        try:
            data = self._call_api("search.messages", {"query": query, "count": min(limit, 100)})
            if not data.get("ok"):
                return f"Slack search error: {data.get('error', 'unknown')}"
            matches = data.get("messages", {}).get("matches", [])
            if not matches:
                return f"No Slack messages found for '{query}'."
            lines = [f"💬 **Slack Search: '{query}'** ({len(matches)} results)\n"]
            for msg in matches[:limit]:
                channel_name = msg.get("channel", {}).get("name", "unknown")
                user = msg.get("username", msg.get("user", "unknown"))
                text = msg.get("text", "")
                permalink = msg.get("permalink", "")
                lines.append(f"• #{channel_name} @{user}: {text[:180]}\n  🔗 {permalink}")
            return "\n".join(lines)
        except Exception as e:
            return f"Slack search error: {e}"

    def _send_message(self, channel: str, message: str) -> str:
        try:
            ch_id = self._resolve_channel_id(channel)
            data = self._call_api(
                "chat.postMessage",
                post_data={"channel": ch_id, "text": message, "username": "JARVIS"},
            )
            if data.get("ok"):
                return f"✅ Message sent to #{channel} via Slack."
            return f"Slack send error: {data.get('error', 'unknown')}"
        except Exception as e:
            return f"Slack send message error: {e}"

    def health_check(self) -> bool:
        try:
            data = self._call_api("auth.test")
            return data.get("ok", False)
        except Exception:
            return False
