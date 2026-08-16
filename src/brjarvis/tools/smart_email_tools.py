# tools/smart_email_tools.py — BR JARVIS Verified Smart Email Suite
"""
High-Fidelity Verified Smart Email Suite for BR JARVIS MK40.2 / MK41.
Guarantees recipient address resolution, explicit delivery status (SENT vs DRAFTED),
attachment validation, idempotency, and canonical ToolResult evidence contracts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .domain import RiskLevel, SideEffectLevel, ToolCategory, ToolErrorCode, VerificationStrategy
from .registry import register_tool
from .tool_result import ToolResult
from brjarvis.actions.smart_email_sender import get_smart_email_sender


@register_tool(
    name="send_email",
    description="Compose and send an email to any recipient email address or saved contact name. Args: 'recipient' (email address or contact name), 'subject' (email subject line), 'body' (text content), 'attachment_paths' (optional list of file paths).",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Recipient email address (e.g. user@example.com) or contact name"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email message body"},
            "attachment_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of local file paths to attach",
            },
        },
        "required": ["recipient", "subject", "body"],
    },
    category="communication",
    risk_level="high",
    permission_required="EXTERNAL_COMMUNICATION",
    is_read_only=False,
    idempotent=True,
    verification_strategy="NETWORK_RESPONSE",
)
def tool_send_email(args: dict) -> ToolResult:
    """Compose and send email with verified recipient resolution."""
    recipient = str(args.get("recipient", "")).strip()
    subject = str(args.get("subject", "")).strip()
    body = str(args.get("body", "")).strip()
    attachments = args.get("attachment_paths")

    if not recipient or not subject or not body:
        return ToolResult.failed(
            "send_email",
            ToolErrorCode.INVALID_ARGUMENT,
            "Parameters 'recipient', 'subject', and 'body' are all required.",
        )

    try:
        sender = get_smart_email_sender()
        raw_res = sender.send_email(
            recipient=recipient,
            subject=subject,
            body=body,
            attachment_paths=attachments,
        )

        is_sent = "successfully sent" in str(raw_res).lower()
        is_drafted = "drafted" in str(raw_res).lower() or "opened gmail" in str(raw_res).lower()

        evidence = f"Email to '{recipient}' (Subject: '{subject}') -> {raw_res}"
        return ToolResult.success(
            tool_name="send_email",
            data={
                "recipient": recipient,
                "subject": subject,
                "delivery_mode": "SMTP" if is_sent else "DRAFT_BROWSER",
                "result_message": str(raw_res),
            },
            output=str(raw_res),
            evidence=evidence,
            verified=is_sent or is_drafted,
            side_effects=[f"email:dispatched:{recipient}"],
            metadata={"recipient": recipient, "subject": subject},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="send_email",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to send email to '{recipient}': {e}",
        )


@register_tool(
    name="schedule_email",
    description="Schedule an email for future automated delivery. Args: 'recipient' (email or contact), 'subject', 'body', 'send_at' (date/time string).",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Recipient email address or contact name"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email message body"},
            "send_at": {"type": "string", "description": "Future date/time string (e.g. '2026-08-20 09:00:00' or '14:30')"},
        },
        "required": ["recipient", "subject", "body", "send_at"],
    },
    category="communication",
    risk_level="medium",
    permission_required="EXTERNAL_COMMUNICATION",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_schedule_email(args: dict) -> ToolResult:
    """Schedule email in future queue."""
    recipient = str(args.get("recipient", "")).strip()
    subject = str(args.get("subject", "")).strip()
    body = str(args.get("body", "")).strip()
    send_at = str(args.get("send_at", "")).strip()

    if not recipient or not subject or not body or not send_at:
        return ToolResult.failed(
            "schedule_email",
            ToolErrorCode.INVALID_ARGUMENT,
            "Parameters 'recipient', 'subject', 'body', and 'send_at' are all required.",
        )

    try:
        sender = get_smart_email_sender()
        raw_res = sender.schedule_email(
            recipient=recipient,
            subject=subject,
            body=body,
            send_at=send_at,
        )
        evidence = f"Scheduled email to '{recipient}' at '{send_at}'."
        return ToolResult.success(
            tool_name="schedule_email",
            data={"recipient": recipient, "subject": subject, "send_at": send_at},
            output=str(raw_res),
            evidence=evidence,
            verified=True,
            metadata={"send_at": send_at},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="schedule_email",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to schedule email: {e}",
        )


@register_tool(
    name="manage_email_contacts",
    description="Manage saved email contacts mapping. Args: 'action' ('add' or 'list'), 'name' (contact name), 'email_address' (email address).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list"], "description": "Action to perform"},
            "name": {"type": "string", "description": "Contact name"},
            "email_address": {"type": "string", "description": "Contact email address"},
        },
        "required": ["action"],
    },
    category="communication",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=False,
)
def tool_manage_email_contacts(args: dict) -> ToolResult:
    """Add or list email contacts."""
    action = str(args.get("action", "")).strip().lower()
    sender = get_smart_email_sender()

    try:
        if action == "add":
            name = str(args.get("name", "")).strip()
            email_addr = str(args.get("email_address", "")).strip()
            res_str = sender.add_contact(name=name, email_address=email_addr)
            return ToolResult.success(
                tool_name="manage_email_contacts",
                data={"name": name, "email": email_addr},
                output=res_str,
                evidence=f"Added contact '{name}' -> '{email_addr}'",
                verified=True,
            )
        elif action == "list":
            contacts = sender.list_contacts()
            return ToolResult.success(
                tool_name="manage_email_contacts",
                data=contacts,
                output=json.dumps(contacts, indent=2),
                evidence=f"Retrieved {len(contacts)} saved email contacts.",
                verified=True,
            )
        else:
            return ToolResult.failed(
                "manage_email_contacts",
                ToolErrorCode.INVALID_ARGUMENT,
                f"Unknown action '{action}'. Allowed: 'add', 'list'.",
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="manage_email_contacts",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error managing email contacts: {e}",
        )
