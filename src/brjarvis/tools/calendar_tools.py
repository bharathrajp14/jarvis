# tools/calendar_tools.py — BR-Jarvis Calendar & Task Tools Plugin
"""
Calendar & Task Tools Plugin for JARVIS.
Exposes tools for creating calendar events, listing upcoming tasks,
searching events, and deleting items.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from .registry import register_tool
from actions.calendar_engine import get_calendar_engine


@register_tool(
    name="create_calendar_event",
    description="Create a calendar event or task (like Mobile Gemini). Args: 'title' (event title), 'start_time' (e.g. 'tomorrow 3pm', '2026-08-01 10:00', 'in 2 hours'), 'end_time' (optional), 'description' (optional), 'location' (optional), 'attendees' (optional list of contacts/emails), 'reminder_minutes' (default: 15), 'notify_whatsapp' (boolean).",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title or task summary"},
            "start_time": {"type": "string", "description": "Start time expression (e.g. 'tomorrow 3pm', 'in 2 hours', '2026-08-01 10:00')"},
            "end_time": {"type": "string", "description": "Optional end time expression"},
            "description": {"type": "string", "description": "Optional event details/notes"},
            "location": {"type": "string", "description": "Optional event location or meeting link"},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of attendee contacts or phone numbers"
            },
            "reminder_minutes": {"type": "integer", "description": "Minutes before event to alert (default: 15)"},
            "notify_whatsapp": {"type": "boolean", "description": "Whether to send WhatsApp invites to attendees"}
        },
        "required": ["title", "start_time"]
    }
)
def tool_create_calendar_event(args: dict) -> str:
    """Create a calendar event or task."""
    title = str(args.get("title", "")).strip()
    start_time = str(args.get("start_time", "")).strip()

    if not title or not start_time:
        return "Error: Both 'title' and 'start_time' are required."

    engine = get_calendar_engine()
    res = engine.create_event(
        title=title,
        start_time_str=start_time,
        end_time_str=args.get("end_time"),
        description=args.get("description", ""),
        location=args.get("location", ""),
        attendees=args.get("attendees"),
        reminder_minutes=args.get("reminder_minutes", 15),
        notify_whatsapp=args.get("notify_whatsapp", False)
    )

    if res.get("success"):
        loc_str = f" @ {res['location']}" if res['location'] else ""
        return f"📅 Event Created Successfully! #{res['event_id']}: '{res['title']}' starting at {res['start_time']}{loc_str}."

    return f"Failed to create event: {res.get('error')}"


@register_tool(
    name="list_calendar_events",
    description="List upcoming calendar events and tasks. Args: 'days' (integer number of days to look ahead, default: 7).",
    parameters={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Number of days to retrieve (default: 7)"}
        }
    }
)
def tool_list_calendar_events(args: dict) -> str:
    """List upcoming calendar events."""
    days = args.get("days", 7)
    engine = get_calendar_engine()
    events = engine.list_events(days=days)

    if not events:
        return f"No calendar events scheduled for the next {days} days."

    lines = [f"📅 UPCOMING CALENDAR EVENTS & TASKS (Next {days} days):"]
    for ev in events:
        loc_str = f" | Location: {ev['location']}" if ev['location'] else ""
        att_str = f" | Attendees: {', '.join(ev['attendees'])}" if ev['attendees'] else ""
        lines.append(f" - #{ev['id']} | {ev['start_time']} | '{ev['title']}'{loc_str}{att_str}")

    return "\n".join(lines)


@register_tool(
    name="search_calendar_events",
    description="Search calendar events by title, description, or location keyword.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"}
        },
        "required": ["query"]
    }
)
def tool_search_calendar_events(args: dict) -> str:
    """Search calendar events."""
    query = str(args.get("query", "")).strip()
    if not query:
        return "Error: Search query required."

    engine = get_calendar_engine()
    events = engine.search_events(query)

    if not events:
        return f"No calendar events matched query '{query}'."

    lines = [f"🔍 CALENDAR SEARCH MATCHES FOR '{query}':"]
    for ev in events:
        loc_str = f" @ {ev['location']}" if ev['location'] else ""
        lines.append(f" - #{ev['id']} | {ev['start_time']} | '{ev['title']}'{loc_str}")

    return "\n".join(lines)


@register_tool(
    name="delete_calendar_event",
    description="Delete a calendar event by ID.",
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "integer", "description": "Calendar event ID to delete"}
        },
        "required": ["event_id"]
    }
)
def tool_delete_calendar_event(args: dict) -> str:
    """Delete a calendar event."""
    event_id = args.get("event_id")
    if not event_id:
        return "Error: event_id is required."

    engine = get_calendar_engine()
    success = engine.delete_event(event_id)

    if success:
        return f"✅ Calendar event #{event_id} deleted successfully."
    return f"Failed to delete calendar event #{event_id}."
