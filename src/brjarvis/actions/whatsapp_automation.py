# actions/whatsapp_automation.py — WhatsApp Contact Messaging & Scheduled Automation Engine
"""
WhatsApp Automation Engine for BR-Jarvis.
Supports direct messaging to any contact or phone number via WhatsApp URI & Web protocols,
contact name resolution, attachment sharing, and scheduled message queues.
"""
from __future__ import annotations

import os
import re
import json
import time
import urllib.parse
import webbrowser
import subprocess
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.WhatsAppAutomation")


def _get_contacts_file() -> Path:
    cfg_dir = Path.cwd() / ".jarvis"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "contacts.json"


def _get_scheduled_messages_file() -> Path:
    cfg_dir = Path.cwd() / ".jarvis"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "scheduled_whatsapp.json"


class WhatsAppAutomation:
    """
    WhatsApp Messaging & Contact Automation Engine.
    """

    def __init__(self):
        self.contacts_file = _get_contacts_file()
        self.scheduled_file = _get_scheduled_messages_file()
        self._contacts: Dict[str, str] = self._load_contacts()
        self._scheduled_queue: List[Dict[str, Any]] = self._load_scheduled()
        self._start_scheduler()

    def _load_contacts(self) -> Dict[str, str]:
        if self.contacts_file.exists():
            try:
                data = json.loads(self.contacts_file.read_text(encoding="utf-8"))
                return {k.lower().strip(): str(v).strip() for k, v in data.items()}
            except Exception as e:
                logger.error(f"Failed loading contacts: {e}")
        return {}

    def _save_contacts(self):
        try:
            self.contacts_file.write_text(json.dumps(self._contacts, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed saving contacts: {e}")

    def add_contact(self, name: str, phone_number: str) -> str:
        """Save a contact name to phone number mapping."""
        clean_name = name.strip()
        clean_phone = re.sub(r"[^\d+]", "", phone_number.strip())

        if not clean_name or not clean_phone:
            return "Error: Contact name and valid phone number are required."

        self._contacts[clean_name.lower()] = clean_phone
        self._save_contacts()
        return f"✅ Saved contact '{clean_name}' with number '{clean_phone}'."

    def list_contacts(self) -> Dict[str, str]:
        return dict(self._contacts)

    def resolve_recipient(self, recipient: str) -> tuple[str, str]:
        """
        Resolve a recipient string into (display_name, phone_or_name).
        If recipient matches a contact name, returns (contact_name, phone_number).
        Otherwise returns (recipient, clean_phone_or_raw).
        """
        rec_clean = recipient.strip()
        rec_lower = rec_clean.lower()

        # 1. Primary UnifiedContactStore lookup (vCard contacts, relationship synonyms "Appa", "Amma", "Dad", "Mom")
        try:
            from brjarvis.memory.contact_manager import get_contact_store
            store = get_contact_store()
            match = store.resolve_name(rec_clean)
            if match and match.get("phone_number"):
                return match["name"], match["phone_number"]
        except Exception as e:
            logger.debug(f"UnifiedContactStore resolution error: {e}")

        # 2. Local fallback contacts dictionary
        if rec_lower in self._contacts:
            return rec_clean, self._contacts[rec_lower]

        for c_name, c_phone in self._contacts.items():
            if rec_lower in c_name or c_name in rec_lower:
                return c_name.title(), c_phone

        # 3. Direct numeric phone format
        digits = re.sub(r"[^\d+]", "", rec_clean)
        if len(digits) >= 7:
            return rec_clean, digits

        return rec_clean, rec_clean

    def send_message(self, recipient: str, message_text: str, open_browser: bool = True) -> str:
        """
        Send a WhatsApp message to any contact or phone number.
        Uses WhatsApp URI scheme / WhatsApp Web protocol.
        """
        if not recipient:
            return "Error: Recipient contact name or phone number required."
        if not message_text:
            return "Error: Message text required."

        display_name, phone_or_name = self.resolve_recipient(recipient)
        encoded_text = urllib.parse.quote(message_text)

        # 1. Direct phone number web / app protocol
        if phone_or_name.startswith("+") or phone_or_name.isdigit():
            clean_num = re.sub(r"[^\d]", "", phone_or_name)
            whatsapp_url = f"https://web.whatsapp.com/send?phone={clean_num}&text={encoded_text}"
            whatsapp_uri = f"whatsapp://send?phone={clean_num}&text={encoded_text}"

            logger.info(f"[WhatsApp] Sending message to {display_name} ({clean_num}): '{message_text[:40]}...'")

            if open_browser:
                try:
                    if os.name == "nt":
                        try:
                            os.startfile(whatsapp_uri)
                        except Exception:
                            os.startfile(whatsapp_url)
                    else:
                        try:
                            webbrowser.open(whatsapp_uri)
                        except Exception:
                            webbrowser.open(whatsapp_url)
                    return f"✅ Opened WhatsApp to send message to {display_name} ({clean_num})."
                    logger.info("Opening WhatsApp Web to message %s (%s).", display_name, clean_num)
                    webbrowser.open(whatsapp_url)
                    return (
                        f"✅ Opened WhatsApp Web to message {display_name} ({clean_num}).\n"
                        f"Message text pre-filled: \"{message_text}\"\n"
                        f"Press ENTER in WhatsApp Web to send."
                    )
                except Exception as e:
                    logger.error("Failed to open WhatsApp Web URL: %s", e)
                    return f"❌ Failed to open WhatsApp Web: {e}"

        # 2. Desktop GUI Fallback to search contact name in WhatsApp app
        try:
            from brjarvis.actions.send_message import send_message as gui_send_message
            res = gui_send_message({
                "platform": "whatsapp",
                "receiver": display_name,
                "message_text": message_text
            })
            return res
        except Exception as e:
            return f"Failed to send WhatsApp message to {recipient}: {e}"

    def schedule_message(self, recipient: str, message_text: str, send_time_str: str) -> str:
        """Schedule a WhatsApp message for a future time."""
        ts = self._parse_scheduled_time(send_time_str)
        if not ts:
            return "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM' or 'HH:MM:SS'."

        item = {
            "id": f"wa_sched_{int(time.time())}",
            "recipient": recipient,
            "message": message_text,
            "send_time": send_time_str,
            "target_ts": ts,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        self._scheduled_queue.append(item)
        self._save_scheduled()
        return f"⏰ Scheduled WhatsApp message to '{recipient}' for {send_time_str}."

    def _parse_scheduled_time(self, time_str: str) -> Optional[float]:
        now = datetime.now()
        # Try full datetime format
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.timestamp()
            except ValueError:
                pass

        # Try time format for today
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"):
            try:
                t = datetime.strptime(time_str, fmt).time()
                dt = datetime.combine(now.date(), t)
                if dt <= now:
                    dt += datetime.timedelta(days=1)
                return dt.timestamp()
            except ValueError:
                pass

        return None

    def _load_scheduled(self) -> List[Dict[str, Any]]:
        if self.scheduled_file.exists():
            try:
                data = json.loads(self.scheduled_file.read_text(encoding="utf-8"))
                now = time.time()
                # Filter out stale items scheduled more than 5 minutes in the past
                valid = [item for item in data if item.get("target_ts", 0) > (now - 300)]
                return valid
            except Exception:
                pass
        return []

    def _save_scheduled(self):
        try:
            self.scheduled_file.write_text(json.dumps(self._scheduled_queue, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _start_scheduler(self):
        t = threading.Thread(target=self._scheduler_loop, daemon=True)
        t.start()

    def _scheduler_loop(self):
        while True:
            now = time.time()
            due_items = [item for item in self._scheduled_queue if item.get("target_ts", 0) <= now]

            if due_items:
                remaining = [item for item in self._scheduled_queue if item.get("target_ts", 0) > now]
                self._scheduled_queue = remaining
                self._save_scheduled()

                for item in due_items:
                    # Ignore old stale items (older than 5 minutes)
                    if (now - item.get("target_ts", 0)) < 300:
                        logger.info(f"[WhatsApp Scheduler] ⏰ Triggering scheduled message to {item['recipient']}")
                        self.send_message(item["recipient"], item["message_text"])

            time.sleep(10)


# Lazy singleton instance
_whatsapp_instance: Optional[WhatsAppAutomation] = None


def get_whatsapp_automation() -> WhatsAppAutomation:
    global _whatsapp_instance
    if _whatsapp_instance is None:
        _whatsapp_instance = WhatsAppAutomation()
    return _whatsapp_instance
