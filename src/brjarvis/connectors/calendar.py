# connectors/calendar.py — Google Calendar & Task Connector
"""
Google Calendar & Task Management Connector for BR JARVIS.
Integrates with Google Calendar API and local calendar engine to schedule events,
list upcoming meetings, and search event schedules.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from brjarvis.actions.calendar_engine import get_calendar_engine

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Calendar")


class CalendarConnector(BaseConnector):
    @property
    def connector_id(self) -> str:
        return "calendar"

    @property
    def display_name(self) -> str:
        return "Google Calendar & Tasks"

    @property
    def description(self) -> str:
        return "Schedule meetings, list upcoming events, and manage calendar appointments"

    @property
    def icon(self) -> str:
        return "📅"

    @property
    def requires_auth(self) -> bool:
        return False

    @property
    def is_configured(self) -> bool:
        return True

    @property
    def auth_hint(self) -> str:
        return "Optional: Save OAuth credentials.json in root folder for cloud Google Calendar sync."

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="create_event",
                description="Create a calendar event or scheduled task with start time and details",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title or task summary"},
                        "start_time": {
                            "type": "string",
                            "description": "Start time (e.g. 'tomorrow 3pm', '2026-08-01 10:00')",
                        },
                        "end_time": {"type": "string", "description": "Optional end time"},
                        "description": {"type": "string", "description": "Optional event details/notes"},
                        "location": {"type": "string", "description": "Optional event location or meeting URL"},
                        "reminder_minutes": {
                            "type": "integer",
                            "description": "Reminder alert in minutes",
                            "default": 15,
                        },
                    },
                    "required": ["title", "start_time"],
                },
            ),
            ConnectorTool(
                name="list_events",
                description="List upcoming calendar events and appointments",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of events to list", "default": 10},
                        "days": {"type": "integer", "description": "Lookahead window in days", "default": 7},
                    },
                },
            ),
            ConnectorTool(
                name="search_events",
                description="Search calendar events by title or keyword",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Keyword to search for in event titles/descriptions",
                        },
                    },
                    "required": ["query"],
                },
            ),
            ConnectorTool(
                name="delete_event",
                description="Delete a scheduled calendar event by its event ID",
                parameters={
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "The unique event ID to delete"},
                    },
                    "required": ["event_id"],
                },
            ),
        ]

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        engine = get_calendar_engine()
        norm_tool = tool_name.lower().replace("calendar_", "").replace("get_", "")

        if norm_tool in ("create_event", "create", "schedule", "add_event"):
            title = str(args.get("title") or args.get("summary") or args.get("name") or "").strip()
            start_time = str(args.get("start_time") or args.get("time") or args.get("start") or "").strip()
            if not title or not start_time:
                return "Error: Both 'title' and 'start_time' are required."
            res = engine.create_event(
                title=title,
                start_time_str=start_time,
                end_time_str=args.get("end_time") or args.get("end"),
                description=args.get("description", ""),
                location=args.get("location", ""),
                reminder_minutes=int(args.get("reminder_minutes") or 15),
            )
            if res.get("success"):
                loc_str = f" @ {res['location']}" if res.get("location") else ""
                return (
                    f"📅 Event Created! #{res['event_id']}: '{res['title']}' starting at {res['start_time']}{loc_str}."
                )
            return f"Failed to create event: {res.get('error', 'Unknown error')}"

        elif norm_tool in ("list_events", "list", "upcoming", "events", "agenda"):
            days = int(args.get("days") or args.get("days_ahead") or 7)
            limit = int(args.get("limit") or 10)
            events = engine.list_events(days=days)
            if limit and isinstance(events, list):
                events = events[:limit]

            if not events:
                return f"📅 No scheduled calendar events found in the next {days} days."

            lines = [f"📅 **Upcoming Calendar Events (Next {days} days):**"]
            for ev in events:
                eid = ev.get("id") or ev.get("event_id")
                loc = f" (Location: {ev['location']})" if ev.get("location") else ""
                lines.append(f"• #{eid} **{ev['title']}** — {ev['start_time']}{loc}")
            return "\n".join(lines)

        elif norm_tool in ("search_events", "search", "find"):
            query = str(args.get("query") or args.get("q") or args.get("keyword") or "").strip()
            if not query:
                return "Please provide a search keyword."
            events = engine.search_events(query=query)
            if not events:
                return f"📅 No calendar events found matching '{query}'."

            lines = [f"📅 **Calendar Search Results for '{query}':**"]
            for ev in events:
                eid = ev.get("id") or ev.get("event_id")
                lines.append(f"• #{eid} **{ev['title']}** — {ev['start_time']}")
            return "\n".join(lines)

        elif norm_tool in ("delete_event", "delete", "remove", "cancel"):
            event_id = str(args.get("event_id") or args.get("id") or "").strip()
            if not event_id:
                return "Error: 'event_id' is required."
            res = engine.delete_event(int(event_id) if event_id.isdigit() else event_id)
            if res.get("success"):
                return f"📅 Event #{event_id} deleted successfully."
            return f"Failed to delete event: {res.get('error', 'Event not found')}"

        return f"Unknown tool '{tool_name}' for Calendar connector."

    def health_check(self) -> bool:
        return True
