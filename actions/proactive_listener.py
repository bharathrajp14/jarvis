# actions/proactive_listener.py — BR JARVIS Autonomous Proactive Multi-Channel Listener
"""
Continuous background listening engine for BR JARVIS MK38.
Monitors incoming Emails (IMAP/Gmail) and WhatsApp messages, extracts intent/entities,
and queues interactive user actions (Reply, Add to Calendar, Dismiss).
"""
from __future__ import annotations

import asyncio
import datetime
import hashlib

import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("JARVIS.ProactiveListener")

# Path to persistent message deduplication database
DB_PATH = Path("memory/processed_messages.db")


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH, timeout=15.0) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                msg_id TEXT PRIMARY KEY,
                channel TEXT,
                sender TEXT,
                snippet TEXT,
                intent TEXT,
                extracted_entities TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


_init_db()


class ProactiveMultiChannelListener:
    """Daemon listener for Emails, WhatsApp messages, and System Alerts."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.running = False
        self.poll_interval = 30  # seconds
        self._thread: Optional[threading.Thread] = None
        self.pending_actions: List[Dict[str, Any]] = []

    def start(self, poll_interval: int = 30):
        """Start the background monitoring thread."""
        if self.running:
            return "Listener is already running."

        self.poll_interval = poll_interval
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ProactiveListenerThread")
        self._thread.start()
        logger.info("Proactive Multi-Channel Listener started (interval: %ds)", poll_interval)
        return f"Proactive Multi-Channel Listener started successfully (polling every {poll_interval}s)."

    def stop(self):
        """Stop the background monitoring thread."""
        if not self.running:
            return "Listener is not running."

        self.running = False
        logger.info("Proactive Multi-Channel Listener stopping...")
        return "Proactive Multi-Channel Listener stopped."

    def get_status(self) -> Dict[str, Any]:

        return {
            "running": self.running,
            "poll_interval": self.poll_interval,
            "pending_action_count": len(self.pending_actions),
        }

    def _is_processed(self, msg_id: str) -> bool:
        try:
            with sqlite3.connect(DB_PATH, timeout=15.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM processed_messages WHERE msg_id = ?", (msg_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.debug("DB check error: %s", e)
            return False

    def _mark_processed(self, msg_id: str, channel: str, sender: str, snippet: str, intent: str, entities: dict):
        try:
            with sqlite3.connect(DB_PATH, timeout=15.0) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO processed_messages (msg_id, channel, sender, snippet, intent, extracted_entities, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'PENDING_USER_APPROVAL')
                    """,
                    (msg_id, channel, sender, snippet, intent, json.dumps(entities))
                )
                conn.commit()
        except Exception as e:
            logger.error("DB mark processed error: %s", e)

    def _run_loop(self):
        """Background thread execution loop."""
        while self.running:
            try:
                self._check_unread_emails()
                self._check_whatsapp_messages()
            except Exception as e:
                logger.error("Error in Proactive Listener loop: %s", e)

            for _ in range(self.poll_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_unread_emails(self):
        """Poll unread emails and classify intent."""
        try:
            from actions.smart_email_sender import get_smart_email_sender
            sender_engine = get_smart_email_sender()
            # Mock or actual check
            # For demonstration & resilience, check IMAP or environment state
            unread_emails = sender_engine.fetch_unread_emails() if hasattr(sender_engine, "fetch_unread_emails") else []
            for email_data in unread_emails:
                msg_id = hashlib.md5(f"email_{email_data.get('id', email_data.get('subject'))}".encode()).hexdigest()
                if self._is_processed(msg_id):
                    continue

                subject = email_data.get("subject", "")
                sender = email_data.get("sender", "Unknown Sender")
                body = email_data.get("body", "")
                snippet = f"[{subject}] {body[:150]}"

                intent, entities = self._classify_message(snippet)
                self._mark_processed(msg_id, "EMAIL", sender, snippet, intent, entities)

                action_item = {
                    "id": msg_id,
                    "channel": "EMAIL",
                    "sender": sender,
                    "subject": subject,
                    "snippet": snippet,
                    "intent": intent,
                    "entities": entities,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "suggested_actions": self._build_suggested_actions(intent, entities, sender, snippet)
                }
                self.pending_actions.append(action_item)
                self._notify_user(action_item)
        except Exception as e:
            logger.debug("Email check skipped/error: %s", e)

    def _check_whatsapp_messages(self):
        """Poll incoming WhatsApp messages."""
        try:
            from actions.whatsapp_automation import get_whatsapp_automation
            wa = get_whatsapp_automation()
            unread_msgs = wa.fetch_unread_messages() if hasattr(wa, "fetch_unread_messages") else []
            for msg in unread_msgs:
                sender = msg.get("sender", "Unknown WhatsApp Contact")
                text = msg.get("text", "")
                msg_id = hashlib.md5(f"wa_{sender}_{text}".encode()).hexdigest()

                if self._is_processed(msg_id):
                    continue

                intent, entities = self._classify_message(text)
                self._mark_processed(msg_id, "WHATSAPP", sender, text[:150], intent, entities)

                action_item = {
                    "id": msg_id,
                    "channel": "WHATSAPP",
                    "sender": sender,
                    "snippet": text[:150],
                    "intent": intent,
                    "entities": entities,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "suggested_actions": self._build_suggested_actions(intent, entities, sender, text)
                }
                self.pending_actions.append(action_item)
                self._notify_user(action_item)
        except Exception as e:
            logger.debug("WhatsApp check skipped/error: %s", e)

    def _classify_message(self, text: str) -> tuple[str, dict]:
        """Classify message intent and extract date/time entities."""
        text_lower = text.lower()
        entities = {}

        # Basic meeting detection logic
        if any(k in text_lower for k in ["meet", "meeting", "call", "schedule", "appointment", "zoom", "tomorrow at", "pm", "am"]):
            intent = "MEETING_REQUEST"
            # Basic date/time entity extraction
            import re
            time_match = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))", text)
            date_match = re.search(r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}/\d{1,2})\b", text_lower)
            if time_match:
                entities["time"] = time_match.group(1)
            if date_match:
                entities["date"] = date_match.group(1)
            entities["title"] = f"Meeting with {text[:30]}"
        elif any(k in text_lower for k in ["urgent", "asap", "please send", "help", "need"]):
            intent = "ACTION_REQUIRED"
        elif "?" in text:
            intent = "INQUIRY"
        else:
            intent = "INFORMATIONAL"

        return intent, entities

    def _build_suggested_actions(self, intent: str, entities: dict, sender: str, text: str) -> List[str]:
        actions = ["reply", "dismiss"]
        if intent == "MEETING_REQUEST" or "date" in entities or "time" in entities:
            actions.append("add_to_calendar")
        return actions

    def _notify_user(self, item: Dict[str, Any]):
        """Proactively notify user via Voice TTS & Desktop Toast."""
        channel = item["channel"]
        sender = item["sender"]
        intent = item["intent"]

        msg = f"New {channel} from {sender}."
        if intent == "MEETING_REQUEST":
            msg += " Meeting request detected. Would you like to add it to your calendar or reply?"
        elif intent == "ACTION_REQUIRED":
            msg += " Action required. Would you like to review and reply?"

        # Voice notification fallback
        try:
            from voice.tts import TextToSpeechEngine
            tts = TextToSpeechEngine()
            tts.speak(msg)
        except Exception:
            pass

        logger.info("[PROACTIVE NOTIFICATION] %s", msg)


_listener_instance = ProactiveMultiChannelListener()


def get_proactive_listener() -> ProactiveMultiChannelListener:
    return _listener_instance
