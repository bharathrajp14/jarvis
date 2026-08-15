# connectors/telegram.py — Telegram Bot Connector
"""
Telegram Bot Connector for BR JARVIS.
Allows sending instant alerts, markdown messages, and documents directly to Telegram.
Uses TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS from environment.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Telegram")

_BASE_API = "https://api.telegram.org/bot"


class TelegramConnector(BaseConnector):

    @property
    def _token(self) -> str:
        return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

    @property
    def _allowed_users(self) -> List[str]:
        raw = os.environ.get("TELEGRAM_ALLOWED_USERS", "").strip()
        if not raw:
            return []
        return [u.strip() for u in raw.split(",") if u.strip()]

    @property
    def connector_id(self) -> str:
        return "telegram"

    @property
    def display_name(self) -> str:
        return "Telegram Bot"

    @property
    def description(self) -> str:
        return "Send alerts, status updates, and interactive notifications via Telegram"

    @property
    def icon(self) -> str:
        return "✈️"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    @property
    def auth_hint(self) -> str:
        return (
            "Add TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS to your .env file.\n"
            "Get free token: message @BotFather on Telegram -> /newbot\n"
            "Get your user ID: message @userinfobot"
        )

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="send_message",
                description="Send a text or Markdown message to a Telegram user or channel",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message content to send"},
                        "chat_id": {"type": "string", "description": "Optional Telegram chat ID (defaults to TELEGRAM_ALLOWED_USERS)"},
                    },
                    "required": ["message"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="get_me",
                description="Check the bot's identity and connection status with Telegram servers",
                parameters={"type": "object", "properties": {}},
                requires_auth=True,
            ),
            ConnectorTool(
                name="get_updates",
                description="Retrieve recent incoming messages and updates sent to the bot",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max messages to retrieve (1-100)", "default": 5},
                    },
                },
                requires_auth=True,
            ),
        ]

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if not self.is_configured:
            return f"Telegram bot is not configured. {self.auth_hint}"

        if tool_name == "send_message":
            msg = str(args.get("message") or args.get("text") or "").strip()
            chat_id = str(args.get("chat_id") or "").strip()
            return self._send_message(msg, chat_id)
        elif tool_name == "get_me":
            return self._get_me()
        elif tool_name == "get_updates":
            limit = int(args.get("limit", 5))
            return self._get_updates(limit)
        return f"Unknown tool '{tool_name}' for Telegram connector."

    def _api_call(self, endpoint: str, payload: Optional[dict] = None) -> dict:
        url = f"{_BASE_API}{self._token}/{endpoint}"
        data = None
        headers = {"User-Agent": "JARVIS-TelegramConnector/1.0"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _send_message(self, text: str, chat_id: Optional[str] = None) -> str:
        if not text:
            return "Error: Message text cannot be empty."

        target_id = chat_id
        if not target_id:
            allowed = self._allowed_users
            if allowed:
                target_id = allowed[0]
            else:
                return "Error: No chat_id provided and TELEGRAM_ALLOWED_USERS is not set in .env."

        try:
            payload = {
                "chat_id": target_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            res = self._api_call("sendMessage", payload)
            if res.get("ok"):
                return f"✈️ Message sent successfully to Telegram chat `{target_id}`."
            return f"Telegram API error: {res.get('description', 'Unknown error')}"
        except Exception as e:
            return f"Failed to send Telegram message: {e}"

    def _get_me(self) -> str:
        try:
            res = self._api_call("getMe")
            if res.get("ok"):
                user = res.get("result", {})
                return (
                    f"✈️ **Telegram Bot Connected**\n"
                    f"• Name: {user.get('first_name', 'Bot')}\n"
                    f"• Username: @{user.get('username', 'unknown')}\n"
                    f"• Bot ID: {user.get('id')}\n"
                    f"• Can Join Groups: {user.get('can_join_groups', False)}"
                )
            return f"Telegram error: {res.get('description', 'Unknown error')}"
        except Exception as e:
            return f"Failed to connect to Telegram: {e}"

    def _get_updates(self, limit: int = 5) -> str:
        try:
            payload = {"limit": limit, "timeout": 2}
            res = self._api_call("getUpdates", payload)
            if not res.get("ok"):
                return f"Telegram error: {res.get('description', 'Unknown error')}"

            updates = res.get("result", [])
            if not updates:
                return "✈️ No recent messages found in bot inbox."

            lines = [f"✈️ **Recent Telegram Messages ({len(updates)}):**"]
            for u in updates[-limit:]:
                msg = u.get("message", {})
                from_user = msg.get("from", {}).get("first_name", "Unknown")
                text = msg.get("text", "[Non-text message]")
                date = msg.get("date", "")
                chat_id = msg.get("chat", {}).get("id", "")
                lines.append(f"• **{from_user}** (ID: `{chat_id}`): {text}")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to fetch Telegram updates: {e}"

    def health_check(self) -> bool:
        if not self.is_configured:
            return False
        try:
            res = self._api_call("getMe")
            return res.get("ok", False)
        except Exception:
            return False
