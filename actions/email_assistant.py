# actions/email_assistant.py — JARVIS MK37 Email Assistant
"""
Email utility assistant for JARVIS MK37.
Supports sending (SMTP), checking (IMAP), and summarizing emails.
"""
from __future__ import annotations

import smtplib
import imaplib
import email
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tools.registry import register_tool


def _sync_auth():
    try:
        from actions.gmail_auth import get_gmail_auth_manager
        get_gmail_auth_manager()
    except Exception:
        pass


def _send_email(to_email: str, subject: str, body: str) -> str:
    _sync_auth()
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()

    if not smtp_user or not smtp_password:
        return (
            "[Offline Mode] SMTP credentials not set. "
            f"Drafted Email:\nTo: {to_email}\nSubject: {subject}\nBody: {body}"
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return f"Email sent successfully to {to_email}."
    except Exception as e:
        return f"ERROR: Failed to send email via SMTP: {e}"


def _fetch_emails(limit: int = 5) -> str:
    _sync_auth()
    imap_server = os.environ.get("IMAP_SERVER", "imap.gmail.com")
    imap_user = os.environ.get("IMAP_USER", "").strip()
    imap_password = os.environ.get("IMAP_PASSWORD", "").strip()

    if not imap_user or not imap_password:
        return (
            "[Offline Mode] IMAP credentials not set. "
            "Mock inbox summary:\n"
            "  1. From: support@github.com - Subject: [GitHub] Security Alert (2 hours ago)\n"
            "  2. From: billing@epicgames.com - Subject: Your receipt for Free Games (1 day ago)\n"
            "  3. From: news@techcrunch.com - Subject: AI Core Redesign Trends in 2026 (2 days ago)"
        )

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(imap_user, imap_password)
        mail.select("inbox")

        status, data = mail.search(None, "ALL")
        mail_ids = data[0].split()
        
        if not mail_ids:
            return "No emails found in inbox."

        lines = ["Recent emails in inbox:"]
        # Fetch up to 'limit' recent emails
        for mail_id in reversed(mail_ids[-limit:]):
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"]
                    sender = msg["from"]
                    lines.append(f"  ● From: {sender}\n    Subject: {subject}")
                    
        mail.logout()
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: Failed to read emails via IMAP: {e}"


@register_tool(
    name="email_assistant",
    description="Send emails via SMTP, check recent inbox messages via IMAP, or draft mail templates.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "send, check, draft"},
            "to": {"type": "string", "description": "Recipient email address (required for action='send')"},
            "subject": {"type": "string", "description": "Subject of the email (required for action='send'/'draft')"},
            "body": {"type": "string", "description": "Body text of the email"},
            "limit": {"type": "integer", "description": "Max emails to check (default 5)"},
        },
        "required": ["action"],
    }
)
def tool_email_assistant(args: dict) -> str:
    action = args.get("action", "check").lower()
    to_email = args.get("to", "")
    subject = args.get("subject", "")
    body = args.get("body", "")
    limit = args.get("limit", 5)

    if action == "send":
        if not to_email or not subject or not body:
            return "ERROR: 'to', 'subject', and 'body' parameters are required to send an email."
        return _send_email(to_email, subject, body)

    elif action == "draft":
        if not subject:
            return "ERROR: 'subject' parameter is required to draft an email."
        draft = f"DRAFT EMAIL TEMPLATE:\nSubject: {subject}\nBody:\n{body or '(Empty body)'}"
        return draft

    else:
        return _fetch_emails(limit)
