# actions/smart_email_sender.py — Smart Email Creation & Automated Sending Engine
"""
Smart Email Creation & Automated Sending Engine for BR-Jarvis.
Supports sending emails to any recipient or saved contact name, file attachments,
scheduled email queues, and web browser compose fallbacks.
"""
from __future__ import annotations

import os
import re
import json
import time
import smtplib
import urllib.parse
import webbrowser
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("JARVIS.SmartEmailSender")


def _get_contacts_file() -> Path:
    cfg_dir = Path.cwd() / ".jarvis"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "email_contacts.json"


def _get_scheduled_file() -> Path:
    cfg_dir = Path.cwd() / ".jarvis"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "scheduled_emails.json"


class SmartEmailSender:
    """
    Engine for creating, scheduling, and sending emails to any recipient.
    """

    def __init__(self):
        self.contacts_file = _get_contacts_file()
        self.scheduled_file = _get_scheduled_file()
        self._contacts: Dict[str, str] = self._load_contacts()
        self._scheduled_queue: List[Dict[str, Any]] = self._load_scheduled()
        self._start_scheduler()

    def _load_contacts(self) -> Dict[str, str]:
        if self.contacts_file.exists():
            try:
                data = json.loads(self.contacts_file.read_text(encoding="utf-8"))
                return {k.lower().strip(): str(v).strip() for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading email contacts: {e}")
        return {}

    def _save_contacts(self):
        try:
            self.contacts_file.write_text(json.dumps(self._contacts, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving email contacts: {e}")

    def add_contact(self, name: str, email_address: str) -> str:
        """Save a contact name to email address mapping."""
        clean_name = name.strip()
        clean_email = email_address.strip()

        if not clean_name or not clean_email or "@" not in clean_email:
            return "Error: Valid contact name and email address required."

        self._contacts[clean_name.lower()] = clean_email
        self._save_contacts()
        return f"✅ Saved email contact '{clean_name}' -> '{clean_email}'."

    def list_contacts(self) -> Dict[str, str]:
        return dict(self._contacts)

    def resolve_recipient(self, recipient: str) -> tuple[str, str]:
        """
        Resolve a recipient string into (display_name, email_address).
        """
        rec_clean = recipient.strip()
        rec_lower = rec_clean.lower()

        # 1. Primary UnifiedContactStore lookup (vCard contacts, relationship synonyms "Appa", "Amma", "Dad", "Mom")
        try:
            from memory.contact_manager import get_contact_store
            store = get_contact_store()
            match = store.resolve_name(rec_clean)
            if match and match.get("email"):
                return match["name"], match["email"]
        except Exception:
            pass

        # 2. Local fallback contacts dictionary
        if rec_lower in self._contacts:
            return rec_clean, self._contacts[rec_lower]

        for c_name, c_email in self._contacts.items():
            if rec_lower in c_name or c_name in rec_lower:
                return c_name.title(), c_email

        # 3. Direct email address format
        if "@" in rec_clean:
            return rec_clean, rec_clean

        return rec_clean, rec_clean

    def _sync_auth(self):
        try:
            from actions.gmail_auth import get_gmail_auth_manager
            get_gmail_auth_manager()
        except Exception:
            pass

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachment_paths: Optional[List[str]] = None,
        open_fallback: bool = True
    ) -> str:
        """
        Send an email to any recipient or contact name.
        Uses authenticated SMTP if credentials exist, or opens Gmail Compose window as fallback.
        """
        if not recipient:
            return "Error: Recipient email address or contact name required."
        if not subject:
            return "Error: Email subject line required."

        self._sync_auth()

        display_name, target_email = self.resolve_recipient(recipient)
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "").strip()
        smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()

        # 1. Try Authenticated SMTP Transmission
        if smtp_user and smtp_password and "@" in target_email:
            try:
                msg = MIMEMultipart()
                msg["From"] = smtp_user
                msg["To"] = target_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                # Add file attachments if provided
                if attachment_paths:
                    for f_path in attachment_paths:
                        p = Path(f_path)
                        if p.exists() and p.is_file():
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(p.read_bytes())
                            encoders.encode_base64(part)
                            part.add_header("Content-Disposition", f"attachment; filename={p.name}")
                            msg.attach(part)

                server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, target_email, msg.as_string())
                server.quit()
                return f"📧 Email successfully sent via SMTP to '{display_name}' ({target_email})."
            except Exception as e:
                logger.error(f"SMTP transmission error: {e}")

        # 2. Fallback to Web Browser Gmail Compose Window
        if open_fallback:
            enc_to = urllib.parse.quote(target_email)
            enc_sub = urllib.parse.quote(subject)
            enc_body = urllib.parse.quote(body)
            gmail_compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={enc_to}&su={enc_sub}&body={enc_body}"

            try:
                webbrowser.open(gmail_compose_url)
                return f"🌐 Drafted email to '{display_name}' ({target_email}) and opened Gmail Compose window in browser."
            except Exception as e:
                return f"Error opening email compose window: {e}"

        return (
            f"[Offline Mode] Drafted email for '{display_name}' ({target_email}):\n"
            f"Subject: {subject}\nBody: {body[:100]}..."
        )

    def schedule_email(self, recipient: str, subject: str, body: str, send_at: str) -> str:
        """
        Schedule an email for future delivery.
        """
        target_ts = self._parse_scheduled_time(send_at)
        if not target_ts:
            return f"Error: Could not parse scheduled time '{send_at}'. Use format 'YYYY-MM-DD HH:MM:SS' or 'HH:MM'."

        entry = {
            "id": int(time.time() * 1000),
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "send_at_str": send_at,
            "target_ts": target_ts,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._scheduled_queue.append(entry)
        self._save_scheduled()
        return f"⏰ Scheduled email to '{recipient}' for {send_at}."

    def _parse_scheduled_time(self, time_str: str) -> Optional[float]:
        now = datetime.now()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.timestamp()
            except ValueError:
                pass

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
        if self.scheduled_file.exists():
            try:
                return json.loads(self.scheduled_file.read_text(encoding="utf-8"))
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
                    print(f"[Email Scheduler] ⏰ Triggering scheduled email to {item['recipient']}")
                    self.send_email(item["recipient"], item["subject"], item["body"])

            time.sleep(10)


# Global singleton instance
_email_sender_instance = SmartEmailSender()


def get_smart_email_sender() -> SmartEmailSender:
    return _email_sender_instance
