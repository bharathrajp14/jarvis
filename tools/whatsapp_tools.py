# tools/whatsapp_tools.py — BR-Jarvis WhatsApp Automation Tools Plugin
"""
WhatsApp Automation Tools Plugin for JARVIS.
Exposes tools for sending instant WhatsApp messages to contacts or phone numbers,
scheduling future WhatsApp messages, and managing saved contacts.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from tools.registry import register_tool
from actions.whatsapp_automation import get_whatsapp_automation


@register_tool(
    name="send_whatsapp",
    description="Send a WhatsApp message directly to any contact name (e.g. 'Mom', 'John') or phone number (e.g. '+1234567890').",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Contact name or phone number with country code"},
            "message": {"type": "string", "description": "Message content to send"}
        },
        "required": ["recipient", "message"]
    }
)
def tool_send_whatsapp(args: dict) -> str:
    """Send WhatsApp message to recipient."""
    recipient = str(args.get("recipient", "")).strip()
    message = str(args.get("message", "")).strip()

    if not recipient or not message:
        return "Error: Both 'recipient' and 'message' are required."

    wa = get_whatsapp_automation()
    return wa.send_message(recipient=recipient, message_text=message)


@register_tool(
    name="schedule_whatsapp_message",
    description="Schedule a WhatsApp message to be automatically sent to a contact at a specified future date/time.",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Contact name or phone number"},
            "message": {"type": "string", "description": "Message content to send"},
            "send_at": {"type": "string", "description": "Target date/time string (e.g. '2026-08-01 09:00:00' or '14:30')"}
        },
        "required": ["recipient", "message", "send_at"]
    }
)
def tool_schedule_whatsapp_message(args: dict) -> str:
    """Schedule a WhatsApp message for future delivery."""
    recipient = str(args.get("recipient", "")).strip()
    message = str(args.get("message", "")).strip()
    send_at = str(args.get("send_at", "")).strip()

    if not recipient or not message or not send_at:
        return "Error: 'recipient', 'message', and 'send_at' are all required."

    wa = get_whatsapp_automation()
    return wa.schedule_message(recipient=recipient, message_text=message, send_at=send_at)


@register_tool(
    name="manage_whatsapp_contacts",
    description="Add a new contact mapping or list saved contacts. Args: 'action' ('add' or 'list'), 'name' (contact name), 'phone_number' (phone number).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list"], "description": "Action to perform"},
            "name": {"type": "string", "description": "Contact display name"},
            "phone_number": {"type": "string", "description": "Phone number with country code"}
        },
        "required": ["action"]
    }
)
def tool_manage_whatsapp_contacts(args: dict) -> str:
    """Manage saved contacts mapping."""
    action = str(args.get("action", "")).strip().lower()
    wa = get_whatsapp_automation()

    if action == "add":
        name = str(args.get("name", "")).strip()
        phone = str(args.get("phone_number", "")).strip()
        return wa.add_contact(name=name, phone_number=phone)

    elif action == "list":
        contacts = wa.list_contacts()
        if not contacts:
            return "No saved WhatsApp contacts found."
        lines = ["📇 SAVED WHATSAPP CONTACTS:"]
        for c_name, c_phone in contacts.items():
            lines.append(f" - {c_name.title()}: {c_phone}")
        return "\n".join(lines)

    return "Unknown action. Supported actions: 'add', 'list'."
