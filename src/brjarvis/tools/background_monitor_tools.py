# tools/background_monitor_tools.py — JARVIS Topic Monitor Tool Wrappers
from __future__ import annotations

from .registry import register_tool
from brjarvis.actions.background_monitor import add_monitor, remove_monitor, list_monitors, check_all


@register_tool(
    name="add_background_monitor",
    description="Add a new topic for JARVIS to monitor daily via background news checks (e.g. AI research, space, tech release). Blocks crypto/financial clutter.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic or keyword to monitor daily."}
        },
        "required": ["topic"]
    }
)
def tool_add_background_monitor(topic: str) -> str:
    return add_monitor(topic)


@register_tool(
    name="remove_background_monitor",
    description="Stop monitoring a previously added news topic.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Monitored topic or keyword to remove."}
        },
        "required": ["topic"]
    }
)
def tool_remove_background_monitor(topic: str) -> str:
    return remove_monitor(topic)


@register_tool(
    name="list_monitored_topics",
    description="List all topics currently monitored by JARVIS.",
    parameters={"type": "object", "properties": {}}
)
def tool_list_monitored_topics() -> str:
    topics = list_monitors()
    if not topics:
        return "No topics are currently being monitored."
    return "Monitored Topics:\n" + "\n".join(f"- {t}" for t in topics)


@register_tool(
    name="check_monitored_topics",
    description="Manually trigger an immediate check across all monitored topics for new headlines.",
    parameters={"type": "object", "properties": {}}
)
def tool_check_monitored_topics() -> str:
    alerts = check_all()
    if not alerts:
        return "Checked all monitored topics. No new headlines found."
    return "\n\n".join(alerts)
