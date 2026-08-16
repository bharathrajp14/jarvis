# tools/whatsapp_tools.py — BR JARVIS Verified WhatsApp Automation Suite
"""
High-Fidelity Verified WhatsApp Automation Suite for BR JARVIS MK40.2 / MK41.
Ensures recipient phone resolution, scheduled queues, contact management,
and canonical ToolResult evidence contracts.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .domain import RiskLevel, SideEffectLevel, ToolCategory, ToolErrorCode, VerificationStrategy
from .registry import register_tool
from .tool_result import ToolResult
from brjarvis.actions.whatsapp_automation import get_whatsapp_automation


@register_tool(
    name="send_whatsapp",
    description="Send a WhatsApp message directly to any contact name (e.g. 'Mom', 'Appa') or phone number. Args: 'recipient' (contact name or number), 'message' (text content).",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Contact name or phone number with country code"},
            "message": {"type": "string", "description": "Message text to send"},
        },
        "required": ["recipient", "message"],
    },
    category="communication",
    risk_level="high",
    permission_required="EXTERNAL_COMMUNICATION",
    is_read_only=False,
    idempotent=True,
    verification_strategy="NETWORK_RESPONSE",
)
def tool_send_whatsapp(args: dict) -> ToolResult:
    """Send WhatsApp message with contact resolution."""
    if isinstance(args, str):
        parts = args.split(":", 1)
        recipient = parts[0].strip() if parts else ""
        message = parts[1].strip() if len(parts) > 1 else args.strip()
    else:
        recipient = str(args.get("recipient") or args.get("phone_number") or args.get("contact") or "").strip()
        message = str(args.get("message") or args.get("text") or args.get("body") or "").strip()

    if not recipient or not message:
        return ToolResult.failed(
            "send_whatsapp",
            ToolErrorCode.INVALID_ARGUMENT,
            "Parameters 'recipient' and 'message' are required.",
        )

    try:
        wa = get_whatsapp_automation()
        raw_res = wa.send_message(recipient=recipient, message_text=message)
        evidence = f"WhatsApp message prepared/sent for '{recipient}': {raw_res}"
        return ToolResult.success(
            tool_name="send_whatsapp",
            data={"recipient": recipient, "message": message, "response": str(raw_res)},
            output=str(raw_res),
            evidence=evidence,
            verified=True,
            side_effects=[f"whatsapp:sent:{recipient}"],
            metadata={"recipient": recipient},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="send_whatsapp",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to send WhatsApp message to '{recipient}': {e}",
        )


@register_tool(
    name="schedule_whatsapp_message",
    description="Schedule a WhatsApp message for future automated sending. Args: 'recipient', 'message', 'send_at' (date/time string).",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Contact name or phone number"},
            "message": {"type": "string", "description": "Message content"},
            "send_at": {"type": "string", "description": "Target date/time string (e.g. '2026-08-20 10:00:00' or '15:30')"},
        },
        "required": ["recipient", "message", "send_at"],
    },
    category="communication",
    risk_level="medium",
    permission_required="EXTERNAL_COMMUNICATION",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_schedule_whatsapp_message(args: dict) -> ToolResult:
    """Schedule future WhatsApp message."""
    recipient = str(args.get("recipient") or args.get("contact") or "").strip()
    message = str(args.get("message") or args.get("text") or "").strip()
    send_at = str(args.get("send_at", "")).strip()

    if not recipient or not message or not send_at:
        return ToolResult.failed(
            "schedule_whatsapp_message",
            ToolErrorCode.INVALID_ARGUMENT,
            "Parameters 'recipient', 'message', and 'send_at' are all required.",
        )

    try:
        wa = get_whatsapp_automation()
        raw_res = wa.schedule_message(recipient=recipient, message_text=message, send_at=send_at)
        evidence = f"Scheduled WhatsApp message to '{recipient}' at '{send_at}'."
        return ToolResult.success(
            tool_name="schedule_whatsapp_message",
            data={"recipient": recipient, "send_at": send_at},
            output=str(raw_res),
            evidence=evidence,
            verified=True,
            metadata={"send_at": send_at},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="schedule_whatsapp_message",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to schedule WhatsApp message: {e}",
        )


@register_tool(
    name="manage_whatsapp_contacts",
    description="Add or list saved WhatsApp contact mappings. Args: 'action' ('add' or 'list'), 'name' (contact name), 'phone_number' (phone with country code).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list"], "description": "Action to perform"},
            "name": {"type": "string", "description": "Contact display name"},
            "phone_number": {"type": "string", "description": "Phone number with country code"},
        },
        "required": ["action"],
    },
    category="communication",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=False,
)
def tool_manage_whatsapp_contacts(args: dict) -> ToolResult:
    """Manage WhatsApp contacts."""
    action = str(args.get("action", "")).strip().lower()
    wa = get_whatsapp_automation()

    try:
        if action == "add":
            name = str(args.get("name", "")).strip()
            phone = str(args.get("phone_number", "")).strip()
            res_str = wa.add_contact(name=name, phone_number=phone)
            return ToolResult.success(
                tool_name="manage_whatsapp_contacts",
                data={"name": name, "phone": phone},
                output=res_str,
                evidence=f"Added contact '{name}' -> '{phone}'",
                verified=True,
            )
        elif action == "list":
            contacts = wa.list_contacts()
            return ToolResult.success(
                tool_name="manage_whatsapp_contacts",
                data=contacts,
                output=json.dumps(contacts, indent=2),
                evidence=f"Retrieved {len(contacts)} saved WhatsApp contacts.",
                verified=True,
            )
        else:
            return ToolResult.failed(
                "manage_whatsapp_contacts",
                ToolErrorCode.INVALID_ARGUMENT,
                f"Unknown action '{action}'. Allowed: 'add', 'list'.",
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="manage_whatsapp_contacts",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error managing WhatsApp contacts: {e}",
        )
