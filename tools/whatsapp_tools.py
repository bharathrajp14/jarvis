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
    description="Send a WhatsApp message or greeting directly to any contact name (e.g. 'Appa', 'Mom', 'John') or phone number. NEVER use open_app or run_code to send WhatsApp messages; ALWAYS use send_whatsapp.",
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
    if isinstance(args, str):
        parts = args.split(":", 1)
        recipient = parts[0].strip() if parts else ""
        message = parts[1].strip() if len(parts) > 1 else args.strip()
    else:
        recipient = str(args.get("recipient") or args.get("phone_number") or args.get("contact") or args.get("to") or args.get("target") or "").strip()
        message = str(args.get("message") or args.get("text") or args.get("body") or args.get("content") or "").strip()

    if not recipient or not message:
        return "Error: Both 'recipient' and 'message' are required for send_whatsapp."

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
    if isinstance(args, str):
        return "Error: 'schedule_whatsapp_message' expects a JSON dictionary."

    recipient = str(args.get("recipient") or args.get("phone_number") or args.get("contact") or args.get("to") or "").strip()
    message = str(args.get("message") or args.get("text") or args.get("body") or args.get("content") or "").strip()
    send_at = str(args.get("send_at") or args.get("time") or args.get("date") or "").strip()

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
def tool_manage_whatsapp_contacts(args: dict | str) -> str:
    """Manage saved contacts mapping."""
    if isinstance(args, str):
        action = args.strip().lower()
        args_dict: dict = {}
    else:
        args_dict = args if isinstance(args, dict) else {}
        action = str(args_dict.get("action") or "list").strip().lower()
    
    wa = get_whatsapp_automation()

    if action in ("add", "save", "create"):
        name = str(args_dict.get("name") or args_dict.get("contact_name") or "").strip()
        phone = str(args_dict.get("phone_number") or args_dict.get("phone") or args_dict.get("number") or "").strip()
        return wa.add_contact(name=name, phone_number=phone)

    elif action in ("list", "show", "get"):
        contacts = wa.list_contacts()
        if not contacts:
            return "No saved WhatsApp contacts found."
        lines = ["📇 SAVED WHATSAPP CONTACTS:"]
        for c_name, c_phone in contacts.items():
            lines.append(f" - {c_name.title()}: {c_phone}")
        return "\n".join(lines)

    return "Unknown action. Supported actions: 'add', 'list'."
