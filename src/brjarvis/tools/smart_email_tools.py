# tools/smart_email_tools.py — BR-Jarvis Smart Email Tools Plugin
"""
Smart Email Tools Plugin for JARVIS.
Exposes tools for composing and sending emails to any recipient or contact,
scheduling emails, and managing email contact address mappings.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from .registry import register_tool
from actions.smart_email_sender import get_smart_email_sender


@register_tool(
    name="send_email",
    description="Compose and send an email to any recipient email address (e.g. 'alex@example.com') or contact name (e.g. 'Alex', 'Manager'). Args: 'recipient', 'subject', 'body', 'attachment_paths' (optional list of file paths).",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Recipient email address or contact name"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body content"},
            "attachment_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of local file paths to attach"
            }
        },
        "required": ["recipient", "subject", "body"]
    }
)
def tool_send_email(args: dict) -> str:
    """Compose and send email to recipient."""
    recipient = str(args.get("recipient", "")).strip()
    subject = str(args.get("subject", "")).strip()
    body = str(args.get("body", "")).strip()
    attachments = args.get("attachment_paths")

    if not recipient or not subject or not body:
        return "Error: 'recipient', 'subject', and 'body' are all required."

    sender = get_smart_email_sender()
    return sender.send_email(
        recipient=recipient,
        subject=subject,
        body=body,
        attachment_paths=attachments
    )


@register_tool(
    name="schedule_email",
    description="Schedule an email for future automated sending to any recipient.",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Recipient email address or contact name"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body content"},
            "send_at": {"type": "string", "description": "Future date/time string (e.g. '2026-08-01 09:00:00' or '14:30')"}
        },
        "required": ["recipient", "subject", "body", "send_at"]
    }
)
def tool_schedule_email(args: dict) -> str:
    """Schedule email for future delivery."""
    recipient = str(args.get("recipient", "")).strip()
    subject = str(args.get("subject", "")).strip()
    body = str(args.get("body", "")).strip()
    send_at = str(args.get("send_at", "")).strip()

    if not recipient or not subject or not body or not send_at:
        return "Error: 'recipient', 'subject', 'body', and 'send_at' are all required."

    sender = get_smart_email_sender()
    return sender.schedule_email(
        recipient=recipient,
        subject=subject,
        body=body,
        send_at=send_at
    )


@register_tool(
    name="manage_email_contacts",
    description="Add or list saved email contact address mappings. Args: 'action' ('add' or 'list'), 'name' (contact name), 'email_address' (email address).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list"], "description": "Action to perform"},
            "name": {"type": "string", "description": "Contact display name"},
            "email_address": {"type": "string", "description": "Contact email address"}
        },
        "required": ["action"]
    }
)
def tool_manage_email_contacts(args: dict) -> str:
    """Manage email contact address mappings."""
    action = str(args.get("action", "")).strip().lower()
    sender = get_smart_email_sender()

    if action == "add":
        name = str(args.get("name", "")).strip()
        email_addr = str(args.get("email_address", "")).strip()
        return sender.add_contact(name=name, email_address=email_addr)

    elif action == "list":
        contacts = sender.list_contacts()
        if not contacts:
            return "No saved email contacts found."
        lines = ["📇 SAVED EMAIL CONTACTS:"]
        for c_name, c_email in contacts.items():
            lines.append(f" - {c_name.title()}: {c_email}")
        return "\n".join(lines)

    return "Unknown action. Supported actions: 'add', 'list'."
