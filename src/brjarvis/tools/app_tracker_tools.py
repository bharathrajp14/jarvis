# tools/app_tracker_tools.py — BR-Jarvis Application Launch Tracker Tools Plugin
"""
Application Launch Tracker Tools Plugin for JARVIS.
Exposes tools for querying application start history logs and usage statistics.
"""
from __future__ import annotations

from typing import Any, Dict
from .registry import register_tool
# NOTE: get_app_tracker is imported lazily inside each handler to prevent a
# missing/broken actions.app_tracker from silently killing all tool registrations.


@register_tool(
    name="get_app_launch_history",
    description="Retrieve the persistent log of application start events recorded on this machine. Args: 'limit' (integer), 'app_name' (optional filter).",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of recent start events to return (default: 30)"},
            "app_name": {"type": "string", "description": "Optional application name filter"}
        }
    }
)
def tool_get_app_launch_history(args: dict) -> str:
    """Retrieve app launch history log."""
    from brjarvis.actions.app_tracker import get_app_tracker  # lazy import
    limit = args.get("limit", 30)
    app_name = str(args.get("app_name", "")).strip()

    tracker = get_app_tracker()
    history = tracker.get_history(limit=limit, app_name=app_name)

    if not history:
        filter_msg = f" for '{app_name}'" if app_name else ""
        return f"No application launch records found{filter_msg}."

    lines = [f"📜 APPLICATION LAUNCH HISTORY ({len(history)} events shown):"]
    for item in history:
        pid_str = f" (PID {item['pid']})" if item['pid'] else ""
        source_str = f"[{item['source']}]"
        lines.append(f" - #{item['id']} | {item['launch_time']} | {source_str} {item['app_name']}{pid_str}")

    return "\n".join(lines)


@register_tool(
    name="get_app_usage_statistics",
    description="Retrieve analytics on application starts, including total launches, most launched apps, and recent activity.",
    parameters={
        "type": "object",
        "properties": {}
    }
)
def tool_get_app_usage_statistics(args: dict) -> str:
    """Retrieve app usage statistics."""
    from brjarvis.actions.app_tracker import get_app_tracker  # lazy import
    tracker = get_app_tracker()
    stats = tracker.get_statistics()

    lines = ["📊 APPLICATION USAGE TELEMETRY & LAUNCH STATS:\n"]
    lines.append(f" - Total App Launch Events Recorded: {stats['total_launches']}")
    lines.append(f" - Unique Applications Launched: {stats['unique_apps']}\n")

    lines.append("🔥 TOP LAUNCHED APPLICATIONS:")
    if stats["most_launched"]:
        for app in stats["most_launched"]:
            lines.append(f"  ● {app['app_name']:<25} | {app['count']} launches | Last: {app['last_launched']}")
    else:
        lines.append("  (No launch statistics available yet)")

    lines.append("\n🕒 RECENT APP STARTS:")
    if stats["recent_launches"]:
        for app in stats["recent_launches"]:
            lines.append(f"  ● {app['app_name']} at {app['launch_time']} [{app['source']}]")
    else:
        lines.append("  (No recent launch events)")

    return "\n".join(lines)
