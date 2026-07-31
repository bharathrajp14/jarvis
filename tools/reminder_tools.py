# tools/reminder_tools.py — OS-Native Reminders Tool Wrappers
from __future__ import annotations

from datetime import datetime, timedelta
from tools.registry import register_tool
from actions.reminder import reminder


@register_tool(
    name="schedule_reminder",
    description="Schedule an OS-native reminder notification.",
    parameters={
        "type": "object",
        "properties": {
            "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format."},
            "time_str": {"type": "string", "description": "Time in HH:MM format (24-hour)."},
            "message": {"type": "string", "description": "Reminder text or notification message."}
        },
        "required": ["date_str", "time_str", "message"]
    }
)
def tool_schedule_reminder(date_str: str, time_str: str, message: str) -> str:
    params = {"date": date_str, "time": time_str, "message": message}
    return reminder(params)
