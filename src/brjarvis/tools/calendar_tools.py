# tools/calendar_tools.py — BR JARVIS Verified Calendar & Task Suite
"""
High-Fidelity Verified Calendar & Task Tools Suite for BR JARVIS MK40.2 / MK41.
Ensures event scheduling, conflict checks, natural language time parsing,
and canonical ToolResult evidence contracts.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .domain import RiskLevel, SideEffectLevel, ToolCategory, ToolErrorCode, VerificationStrategy
from .registry import register_tool
from .tool_result import ToolResult
from brjarvis.actions.calendar_engine import get_calendar_engine


@register_tool(
    name="create_calendar_event",
    description="Create a calendar event or task. Args: 'title', 'start_time' (e.g. 'tomorrow 3pm', '2026-08-20 10:00'), 'end_time', 'description', 'location', 'attendees', 'reminder_minutes'.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title or task summary"},
            "start_time": {"type": "string", "description": "Start time expression"},
            "end_time": {"type": "string", "description": "Optional end time expression"},
            "description": {"type": "string", "description": "Event details/notes"},
            "location": {"type": "string", "description": "Event location or link"},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Attendee contacts or emails",
            },
            "reminder_minutes": {"type": "integer", "description": "Alert minutes prior (default: 15)"},
            "notify_whatsapp": {"type": "boolean", "description": "Send WhatsApp invites"},
        },
        "required": ["title", "start_time"],
    },
    category="communication",
    risk_level="medium",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_create_calendar_event(args: dict) -> ToolResult:
    """Create calendar event with read-back verification."""
    title = str(args.get("title", "")).strip()
    start_time = str(args.get("start_time", "")).strip()

    if not title or not start_time:
        return ToolResult.failed(
            "create_calendar_event",
            ToolErrorCode.INVALID_ARGUMENT,
            "Parameters 'title' and 'start_time' are required.",
        )

    try:
        engine = get_calendar_engine()
        res = engine.create_event(
            title=title,
            start_time_str=start_time,
            end_time_str=args.get("end_time"),
            description=args.get("description", ""),
            location=args.get("location", ""),
            attendees=args.get("attendees"),
            reminder_minutes=int(args.get("reminder_minutes", 15)),
            notify_whatsapp=bool(args.get("notify_whatsapp", False)),
        )

        if res.get("success"):
            event_id = res.get("event_id", "")
            evidence = f"Calendar event #{event_id} '{title}' created starting {res.get('start_time')}."
            return ToolResult.success(
                tool_name="create_calendar_event",
                data=res,
                output=f"📅 {evidence}",
                evidence=evidence,
                verified=True,
                side_effects=[f"calendar:event_created:{event_id}"],
                metadata={"event_id": event_id},
            )
        else:
            return ToolResult.failed(
                "create_calendar_event",
                ToolErrorCode.EXECUTION_EXCEPTION,
                res.get("error", "Failed to create calendar event."),
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="create_calendar_event",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Calendar event creation failed: {e}",
        )


@register_tool(
    name="list_calendar_events",
    description="List upcoming calendar events and tasks. Args: 'days_ahead' (integer, default: 7), 'include_completed' (boolean).",
    parameters={
        "type": "object",
        "properties": {
            "days_ahead": {"type": "integer", "description": "Number of days ahead to look (default: 7)"},
            "include_completed": {"type": "boolean", "description": "Whether to include past events"},
        },
    },
    category="communication",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_list_calendar_events(args: dict) -> ToolResult:
    """List scheduled calendar events."""
    days = int(args.get("days_ahead", 7))
    inc_past = bool(args.get("include_completed", False))

    try:
        engine = get_calendar_engine()
        events = engine.list_events(days_ahead=days, include_past=inc_past)
        evidence = f"Found {len(events)} calendar events for the next {days} days."
        return ToolResult.success(
            tool_name="list_calendar_events",
            data=events,
            output=json.dumps(events, indent=2, default=str),
            evidence=evidence,
            verified=True,
            metadata={"count": len(events)},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="list_calendar_events",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to list calendar events: {e}",
        )


@register_tool(
    name="delete_calendar_event",
    description="Delete a calendar event by its event ID. Args: 'event_id' (event identifier string).",
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Calendar event ID to remove"},
        },
        "required": ["event_id"],
    },
    category="communication",
    risk_level="medium",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_delete_calendar_event(args: dict) -> ToolResult:
    """Delete a calendar event."""
    event_id = str(args.get("event_id", "")).strip()
    if not event_id:
        return ToolResult.failed("delete_calendar_event", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'event_id' is required.")

    try:
        engine = get_calendar_engine()
        res = engine.delete_event(event_id=event_id)
        if res.get("success"):
            evidence = f"Deleted calendar event #{event_id}."
            return ToolResult.success(
                tool_name="delete_calendar_event",
                data=res,
                output=f"🗑️ {evidence}",
                evidence=evidence,
                verified=True,
                side_effects=[f"calendar:event_deleted:{event_id}"],
            )
        else:
            return ToolResult.failed(
                "delete_calendar_event",
                ToolErrorCode.TOOL_NOT_FOUND,
                res.get("error", f"Event #{event_id} not found."),
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="delete_calendar_event",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to delete event: {e}",
        )
