# connectors/gmail.py — Gmail & Email Connector
"""
Gmail & Email Connector for BR JARVIS.
Enables sending automated emails, checking inboxes, and searching emails via SMTP/IMAP.
Uses GMAIL_ADDRESS and GMAIL_APP_PASSWORD from environment or .jarvis/gmail_config.json.
"""
from __future__ import annotations

import email
import imaplib
import json
import logging
import os
import smtplib
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Gmail")


class GmailConnector(BaseConnector):

    @property
    def _email(self) -> str:
        return (
            os.environ.get("GMAIL_ADDRESS")
            or os.environ.get("SMTP_USER")
            or os.environ.get("IMAP_USER")
            or ""
        ).strip()

    @property
    def _password(self) -> str:
        return (
            os.environ.get("GMAIL_APP_PASSWORD")
            or os.environ.get("SMTP_PASSWORD")
            or os.environ.get("IMAP_PASSWORD")
            or ""
        ).strip()

    @property
    def connector_id(self) -> str:
        return "gmail"

    @property
    def display_name(self) -> str:
        return "Gmail & Google Workspace"

    @property
    def description(self) -> str:
        return "Send automated emails, read inbox messages, and search email archives"

    @property
    def icon(self) -> str:
        return "📧"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_configured(self) -> bool:
        return bool(self._email and self._password)

    @property
    def auth_hint(self) -> str:
        return (
            "Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to your .env file.\n"
            "Generate App Password: https://myaccount.google.com/apppasswords"
        )

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="send_email",
                description="Send an email to a recipient with subject and body",
                parameters={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject line"},
                        "body": {"type": "string", "description": "Email body content (plaintext or HTML)"},
                    },
                    "required": ["to", "subject", "body"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="read_inbox",
                description="Fetch the most recent unread or latest emails from the inbox",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of recent emails to fetch", "default": 5},
                        "unread_only": {"type": "boolean", "description": "Only fetch unread messages", "default": True},
                    },
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="search_emails",
                description="Search inbox emails by subject keyword or sender address",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keyword (subject or sender)"},
                        "limit": {"type": "integer", "description": "Max results to return", "default": 5},
                    },
                    "required": ["query"],
                },
                requires_auth=True,
            ),
        ]

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if not self.is_configured:
            return f"Gmail connector is not configured. {self.auth_hint}"

        if tool_name == "send_email":
            to = str(args.get("to") or args.get("recipient") or "").strip()
            subject = str(args.get("subject") or "").strip()
            body = str(args.get("body") or args.get("message") or "").strip()
            return self._send_email(to, subject, body)
        elif tool_name in ("read_inbox", "get_inbox"):
            limit = int(args.get("limit", 5))
            unread = bool(args.get("unread_only", True))
            return self._read_inbox(limit, unread)
        elif tool_name == "search_emails":
            query = str(args.get("query") or "").strip()
            limit = int(args.get("limit", 5))
            return self._search_emails(query, limit)
        return f"Unknown tool '{tool_name}' for Gmail connector."

    def _send_email(self, to_addr: str, subject: str, body: str) -> str:
        if not to_addr or not subject or not body:
            return "Error: 'to', 'subject', and 'body' are all required for send_email."

        try:
            msg = MIMEMultipart()
            msg["From"] = self._email
            msg["To"] = to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain" if "<html" not in body.lower() else "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15.0) as server:
                server.login(self._email, self._password)
                server.sendmail(self._email, [to_addr], msg.as_string())

            return f"📧 Email successfully sent to `{to_addr}` with subject: '{subject}'."
        except Exception as e:
            return f"Failed to send email via SMTP: {e}"

    def _read_inbox(self, limit: int = 5, unread_only: bool = True) -> str:
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mail:
                mail.login(self._email, self._password)
                mail.select("INBOX")

                criterion = "UNSEEN" if unread_only else "ALL"
                status, messages = mail.search(None, criterion)
                if status != "OK" or not messages[0]:
                    status_type = "unread" if unread_only else "recent"
                    return f"📧 No {status_type} emails found in inbox."

                mail_ids = messages[0].split()
                selected_ids = mail_ids[-limit:]
                selected_ids.reverse()

                results = [f"📧 **Inbox Messages ({len(selected_ids)}):**"]
                for num in selected_ids:
                    _, data = mail.fetch(num, "(RFC822.HEADER)")
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    subject_raw = msg.get("Subject", "(No Subject)")
                    decoded_subject = ""
                    for part, encoding in decode_header(subject_raw):
                        if isinstance(part, bytes):
                            decoded_subject += part.decode(encoding or "utf-8", errors="ignore")
                        else:
                            decoded_subject += str(part)

                    from_addr = msg.get("From", "Unknown Sender")
                    date_str = msg.get("Date", "")
                    results.append(f"• **From**: {from_addr}\n  **Subject**: {decoded_subject}\n  **Date**: {date_str}")

                return "\n".join(results)
        except Exception as e:
            return f"Failed to read Gmail inbox via IMAP: {e}"

    def _search_emails(self, query: str, limit: int = 5) -> str:
        if not query:
            return "Please provide a search query."
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mail:
                mail.login(self._email, self._password)
                mail.select("INBOX")

                status, messages = mail.search(None, f'TEXT "{query}"')
                if status != "OK" or not messages[0]:
                    return f"📧 No emails matching '{query}' found in inbox."

                mail_ids = messages[0].split()
                selected_ids = mail_ids[-limit:]
                selected_ids.reverse()

                results = [f"📧 **Search Results for '{query}' ({len(selected_ids)}):**"]
                for num in selected_ids:
                    _, data = mail.fetch(num, "(RFC822.HEADER)")
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    subject_raw = msg.get("Subject", "(No Subject)")
                    decoded_subject = ""
                    for part, encoding in decode_header(subject_raw):
                        if isinstance(part, bytes):
                            decoded_subject += part.decode(encoding or "utf-8", errors="ignore")
                        else:
                            decoded_subject += str(part)

                    from_addr = msg.get("From", "Unknown Sender")
                    results.append(f"• **From**: {from_addr} | **Subject**: {decoded_subject}")

                return "\n".join(results)
        except Exception as e:
            return f"Failed to search Gmail: {e}"

    def health_check(self) -> bool:
        if not self.is_configured:
            return False
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mail:
                mail.login(self._email, self._password)
                return True
        except Exception:
            return False
