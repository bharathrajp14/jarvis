# tools/reminder_tools.py — OS-Native Reminders Tool Wrappers
from __future__ import annotations

from brjarvis.actions.reminder import reminder
from brjarvis.actions.reminders import get_reminder_manager, reminder_tool_action

from .registry import register_tool


@register_tool(
    name="schedule_reminder",
    description="Schedule an OS-native reminder notification.",
    parameters={
        "type": "object",
        "properties": {
            "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format."},
            "time_str": {"type": "string", "description": "Time in HH:MM format (24-hour)."},
            "message": {"type": "string", "description": "Reminder text or notification message."},
        },
        "required": ["date_str", "time_str", "message"],
    },
)
def tool_schedule_reminder(date_str: str, time_str: str, message: str) -> str:
    params = {"date": date_str, "time": time_str, "message": message}
    return reminder(params)


@register_tool(
    name="manage_reminders",
    description="Add, list, or check pending smart desktop reminders with audio alerts.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list"],
                "description": "Action to perform ('add' or 'list').",
            },
            "text": {"type": "string", "description": "Reminder message text (required for 'add')."},
            "delay_seconds": {"type": "integer", "description": "Delay in seconds from now."},
            "time_str": {
                "type": "string",
                "description": "Target time string (e.g. '9:00 AM', '14:30', 'tomorrow 9am').",
            },
        },
        "required": ["action"],
    },
)
def tool_manage_reminders(action: str = "add", text: str = "", delay_seconds: int = 0, time_str: str = "") -> str:
    return reminder_tool_action(action=action, text=text, delay_seconds=delay_seconds, time_str=time_str)


__all__ = [
    "tool_schedule_reminder",
    "tool_manage_reminders",
    "get_reminder_manager",
]
