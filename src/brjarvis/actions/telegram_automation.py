# actions/telegram_automation.py — BR-Jarvis Telegram Bot API Messaging Engine
"""
Telegram Messaging Engine for BR-Jarvis.

Supports direct messaging to any Telegram user (by @username, numeric chat_id,
or saved contact name), group/channel messaging, scheduled message queues,
and a persisted contact book.

Requirements:
  - TELEGRAM_BOT_TOKEN in .env  (get it from @BotFather on Telegram)
  - pip install requests (already in requirements)

Telegram Bot API Limitation:
  A bot can only send messages to users who have FIRST messaged the bot,
  or to groups/channels where the bot has been added as a member.
  This is a Telegram platform rule (not a code limitation).
  
Fallback:
  If TELEGRAM_BOT_TOKEN is not set, falls back to the desktop GUI automation
  (opens Telegram desktop app and uses pyautogui to type the message).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.TelegramAutomation")

# ── Telegram Bot API Base URL ──────────────────────────────────────────────────
_TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _get_bot_token() -> str:
    """Read TELEGRAM_BOT_TOKEN from environment (supports .env via dotenv)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        # Try loading .env manually as a fallback
        try:
            from brjarvis.core.paths import paths
            env_path = paths.ENV_FILE
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("TELEGRAM_BOT_TOKEN=") and not line.startswith("#"):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if token:
                            os.environ["TELEGRAM_BOT_TOKEN"] = token
                            break
        except Exception as e:
            logger.debug(f"Could not read .env for Telegram token: {e}")
    return token


def _get_contacts_file() -> Path:
    from brjarvis.core.paths import paths
    cfg_dir = paths.PROJECT_ROOT / ".jarvis"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "telegram_contacts.json"


def _get_scheduled_file() -> Path:
    from brjarvis.core.paths import paths
    cfg_dir = paths.PROJECT_ROOT / ".jarvis"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "scheduled_telegram.json"


class TelegramAutomation:
    """
    Telegram Messaging & Contact Automation Engine.

    Sends messages via the Telegram Bot API when TELEGRAM_BOT_TOKEN is set,
    with automatic fallback to desktop GUI (Telegram app + pyautogui).
    """

    def __init__(self):
        self._token: str = _get_bot_token()
        self._contacts_file = _get_contacts_file()
        self._scheduled_file = _get_scheduled_file()
        self._contacts: Dict[str, str] = self._load_contacts()
        self._scheduled_queue: List[Dict[str, Any]] = self._load_scheduled()
        self._session = None  # Lazy requests.Session
        self._start_scheduler()

    # ── Internal HTTP session ──────────────────────────────────────────────────

    def _get_session(self):
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update({
                    "User-Agent": "BR-Jarvis/1.0 TelegramBot"
                })
            except ImportError:
                logger.error("'requests' package not installed. Run: pip install requests")
        return self._session

    def _api_call(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a Telegram Bot API call.
        Returns the parsed JSON response dict.
        Raises RuntimeError on failure.
        """
        if not self._token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN not configured. "
                "Add it to your .env file. See .env.template for instructions."
            )

        url = _TELEGRAM_API_BASE.format(token=self._token, method=method)
        session = self._get_session()
        if session is None:
            raise RuntimeError("Failed to initialize requests session.")

        try:
            resp = session.post(url, json=payload, timeout=15)
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Telegram API request failed: {e}") from e

        if not data.get("ok"):
            err_code = data.get("error_code", "?")
            err_desc = data.get("description", "Unknown error")
            raise RuntimeError(
                f"Telegram API error [{err_code}]: {err_desc}"
            )
        return data

    # ── Contact Management ─────────────────────────────────────────────────────

    def _load_contacts(self) -> Dict[str, str]:
        """Load saved contacts from .jarvis/telegram_contacts.json."""
        if self._contacts_file.exists():
            try:
                data = json.loads(self._contacts_file.read_text(encoding="utf-8"))
                return {k.lower().strip(): str(v).strip() for k, v in data.items()}
            except Exception as e:
                logger.error(f"Failed loading Telegram contacts: {e}")
        return {}

    def _save_contacts(self):
        try:
            self._contacts_file.write_text(
                json.dumps(self._contacts, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed saving Telegram contacts: {e}")

    def add_contact(self, name: str, chat_id: str) -> str:
        """
        Save a contact name to Telegram chat_id or @username mapping.

        Args:
            name: Display name (e.g. "Appa", "John", "Team Chat")
            chat_id: Telegram chat_id (numeric string) or @username
        """
        clean_name = name.strip()
        clean_id = chat_id.strip()

        if not clean_name or not clean_id:
            return "❌ Error: Both contact name and Telegram chat_id/@username are required."

        self._contacts[clean_name.lower()] = clean_id
        self._save_contacts()
        return f"✅ Saved Telegram contact '{clean_name}' → '{clean_id}'."

    def list_contacts(self) -> Dict[str, str]:
        """Return all saved Telegram contacts."""
        return dict(self._contacts)

    # ── Recipient Resolution ───────────────────────────────────────────────────

    def resolve_recipient(self, recipient: str) -> Tuple[str, str]:
        """
        Resolve a recipient string into (display_name, chat_id_or_username).

        Resolution order:
          1. Numeric chat_id (e.g. "123456789")
          2. @username (e.g. "@johnsmith")
          3. Saved local contact name
          4. UnifiedContactStore lookup (if available)
          5. Raw value passed through as-is
        """
        rec = recipient.strip()

        # 1. Direct numeric chat_id
        if rec.lstrip("-").isdigit():
            return rec, rec

        # 2. @username format
        if rec.startswith("@"):
            return rec, rec

        # 3. Saved local contacts (case-insensitive)
        rec_lower = rec.lower()
        if rec_lower in self._contacts:
            return rec, self._contacts[rec_lower]

        # Partial name match
        for c_name, c_id in self._contacts.items():
            if rec_lower in c_name or c_name in rec_lower:
                return c_name.title(), c_id

        # 4. UnifiedContactStore (JARVIS shared contact store)
        try:
            from memory.contact_manager import get_contact_store
            store = get_contact_store()
            match = store.resolve_name(rec)
            if match:
                # Try telegram_id field, then phone (can be used as chat_id in some contexts)
                tg_id = match.get("telegram_id") or match.get("telegram")
                if tg_id:
                    return match.get("name", rec), str(tg_id)
        except Exception as e:
            logger.debug(f"UnifiedContactStore lookup failed: {e}")

        # 5. Fall through — pass as-is (user may mean a @username or a saved contact)
        return rec, rec

    # ── Sending ────────────────────────────────────────────────────────────────

    def send_message(
        self,
        recipient: str,
        message_text: str,
        parse_mode: str = "Markdown",
    ) -> str:
        """
        Send a Telegram message to any recipient.

        Args:
            recipient: Contact name, @username, numeric chat_id, or group/channel ID
            message_text: Message content (supports Markdown/HTML)
            parse_mode: "Markdown", "HTML", or "" for plain text

        Returns:
            Status string describing the result.
        """
        if not recipient:
            return "❌ Error: Recipient (contact name, @username, or chat_id) is required."
        if not message_text:
            return "❌ Error: Message text is required."

        display_name, chat_id = self.resolve_recipient(recipient)

        # Try Bot API first
        if self._token:
            return self._send_via_bot_api(
                display_name=display_name,
                chat_id=chat_id,
                message_text=message_text,
                parse_mode=parse_mode,
            )

        # Fallback to desktop GUI automation
        logger.info(
            "[Telegram] No Bot API token — falling back to desktop GUI for %s",
            display_name,
        )
        return self._send_via_desktop_gui(display_name, message_text)

    def _send_via_bot_api(
        self,
        display_name: str,
        chat_id: str,
        message_text: str,
        parse_mode: str = "Markdown",
    ) -> str:
        """Send message via the Telegram Bot API."""
        try:
            payload: Dict[str, Any] = {
                "chat_id": chat_id,
                "text": message_text,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode

            logger.info(
                "[Telegram Bot API] Sending to %s (chat_id=%s): '%s...'",
                display_name, chat_id, message_text[:40],
            )

            result = self._api_call("sendMessage", payload)
            msg_id = result.get("result", {}).get("message_id", "?")
            return (
                f"✅ Telegram message sent to {display_name} (chat_id: {chat_id}).\n"
                f"   Message ID: {msg_id}"
            )

        except RuntimeError as e:
            err_str = str(e)
            # Helpful hint for 'chat not found'
            if "chat not found" in err_str.lower() or "400" in err_str:
                return (
                    f"❌ {e}\n\n"
                    f"💡 Hint: The bot cannot message '{display_name}' yet.\n"
                    f"   Ask them to open Telegram and start a conversation with your bot first:\n"
                    f"   → t.me/<your_bot_username>\n"
                    f"   Or add the bot to a group and use the group's chat_id instead."
                )
            return f"❌ Telegram send failed: {e}"
        except Exception as e:
            logger.error("[Telegram] Unexpected error: %s", e, exc_info=True)
            return f"❌ Telegram error: {e}"

    def _send_via_desktop_gui(self, receiver: str, message_text: str) -> str:
        """Fallback: send via Telegram desktop app using pyautogui."""
        try:
            from actions.send_message import send_message as gui_send
            result = gui_send({
                "platform": "telegram",
                "receiver": receiver,
                "message_text": message_text,
            })
            return result
        except Exception as e:
            return (
                f"❌ Could not send Telegram message to '{receiver}'.\n"
                f"   No bot token configured and desktop GUI fallback failed: {e}\n\n"
                f"💡 Set TELEGRAM_BOT_TOKEN in your .env file to enable reliable messaging."
            )

    # ── Scheduling ─────────────────────────────────────────────────────────────

    def schedule_message(
        self,
        recipient: str,
        message_text: str,
        send_at: str,
    ) -> str:
        """
        Schedule a Telegram message for a future time.

        Args:
            recipient: Contact name, @username, or chat_id
            message_text: Message content
            send_at: Time string e.g. '2026-08-01 09:00' or '14:30'
        """
        ts = self._parse_scheduled_time(send_at)
        if ts is None:
            return "❌ Invalid time format. Use 'YYYY-MM-DD HH:MM', 'HH:MM', or 'HH:MM:SS'."

        item = {
            "id": f"tg_sched_{int(time.time())}",
            "recipient": recipient,
            "message": message_text,
            "send_at": send_at,
            "target_ts": ts,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }
        self._scheduled_queue.append(item)
        self._save_scheduled()

        scheduled_dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        return f"⏰ Telegram message to '{recipient}' scheduled for {scheduled_dt}."

    def _parse_scheduled_time(self, time_str: str) -> Optional[float]:
        """Parse a time string into a UNIX timestamp."""
        now = datetime.now()

        # Full datetime formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ):
            try:
                return datetime.strptime(time_str, fmt).timestamp()
            except ValueError:
                pass

        # Time-only formats (today, or tomorrow if past)
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"):
            try:
                t = datetime.strptime(time_str, fmt).time()
                dt = datetime.combine(now.date(), t)
                if dt <= now:
                    dt += timedelta(days=1)
                return dt.timestamp()
            except ValueError:
                pass

        return None

    def _load_scheduled(self) -> List[Dict[str, Any]]:
        if self._scheduled_file.exists():
            try:
                data = json.loads(self._scheduled_file.read_text(encoding="utf-8"))
                now = time.time()
                # Keep only items scheduled within the next 30 days or up to 5min past
                return [
                    item for item in data
                    if item.get("target_ts", 0) > (now - 300)
                ]
            except Exception:
                pass
        return []

    def _save_scheduled(self):
        try:
            self._scheduled_file.write_text(
                json.dumps(self._scheduled_queue, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _start_scheduler(self):
        t = threading.Thread(target=self._scheduler_loop, daemon=True, name="TelegramScheduler")
        t.start()

    def _scheduler_loop(self):
        """Background thread that fires scheduled messages when due."""
        while True:
            now = time.time()
            due = [item for item in self._scheduled_queue if item.get("target_ts", 0) <= now]

            if due:
                self._scheduled_queue = [
                    item for item in self._scheduled_queue
                    if item.get("target_ts", 0) > now
                ]
                self._save_scheduled()

                for item in due:
                    # Skip stale items older than 5 minutes
                    if (now - item.get("target_ts", 0)) < 300:
                        logger.info(
                            "[Telegram Scheduler] ⏰ Sending scheduled message to %s",
                            item["recipient"],
                        )
                        try:
                            result = self.send_message(item["recipient"], item["message"])
                            logger.info("[Telegram Scheduler] Result: %s", result)
                        except Exception as e:
                            logger.error(
                                "[Telegram Scheduler] Failed to send to %s: %s",
                                item["recipient"], e,
                            )

            time.sleep(10)

    # ── Bot Info ───────────────────────────────────────────────────────────────

    def get_bot_info(self) -> str:
        """Return info about the configured bot (validates the token)."""
        if not self._token:
            return (
                "⚠️ No TELEGRAM_BOT_TOKEN configured.\n"
                "Add TELEGRAM_BOT_TOKEN=<your_token> to your .env file.\n"
                "Get a token from @BotFather on Telegram."
            )
        try:
            data = self._api_call("getMe", {})
            bot = data.get("result", {})
            return (
                f"🤖 Telegram Bot Connected!\n"
                f"   Name: {bot.get('first_name', '?')}\n"
                f"   Username: @{bot.get('username', '?')}\n"
                f"   ID: {bot.get('id', '?')}\n"
                f"   Can join groups: {bot.get('can_join_groups', False)}\n\n"
                f"💡 Share this link with users to allow messaging:\n"
                f"   t.me/{bot.get('username', 'your_bot')}"
            )
        except RuntimeError as e:
            return f"❌ Bot API error: {e}"

    def get_updates(self, limit: int = 10) -> str:
        """
        Fetch recent bot updates (incoming messages).
        Useful for discovering chat_ids of users who have messaged the bot.
        """
        if not self._token:
            return "⚠️ TELEGRAM_BOT_TOKEN not configured."
        try:
            data = self._api_call("getUpdates", {"limit": limit, "timeout": 0})
            updates = data.get("result", [])
            if not updates:
                return (
                    "📭 No recent messages received by the bot.\n"
                    "💡 Ask your contacts to send /start to the bot to enable messaging."
                )
            lines = ["📬 Recent bot interactions (use chat_id to message them):"]
            seen_chats = set()
            for upd in updates:
                msg = upd.get("message") or upd.get("channel_post") or {}
                chat = msg.get("chat", {})
                chat_id = chat.get("id")
                if chat_id and chat_id not in seen_chats:
                    seen_chats.add(chat_id)
                    chat_type = chat.get("type", "?")
                    name = (
                        chat.get("username")
                        or chat.get("title")
                        or f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
                        or "Unknown"
                    )
                    lines.append(f"  • {name} (chat_id: {chat_id}, type: {chat_type})")
            return "\n".join(lines)
        except RuntimeError as e:
            return f"❌ getUpdates error: {e}"


# ── Lazy Singleton ─────────────────────────────────────────────────────────────

_telegram_instance: Optional[TelegramAutomation] = None
_telegram_lock = threading.Lock()


def get_telegram_automation() -> TelegramAutomation:
    """Return the global TelegramAutomation singleton (lazy-initialized)."""
    global _telegram_instance
    if _telegram_instance is None:
        with _telegram_lock:
            if _telegram_instance is None:
                _telegram_instance = TelegramAutomation()
    return _telegram_instance
