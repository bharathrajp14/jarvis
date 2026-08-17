# tools/proactive_listener_tools.py — Proactive Multi-Channel Listener Tools
"""
Tool definitions for managing the proactive multi-channel listener (Email, WhatsApp)
and responding to pending interactive action suggestions (Reply, Add to Calendar, Dismiss).
"""
from __future__ import annotations

from typing import Dict, Any
from .registry import register_tool


@register_tool(
    name="start_multichannel_listener",
    description="Start the proactive background listener monitoring incoming Emails and WhatsApp messages.",
    parameters={
        "type": "object",
        "properties": {
            "poll_interval": {"type": "integer", "description": "Polling interval in seconds (default: 30)"}
        },
        "required": []
    }
)
def start_multichannel_listener_action(args: Dict[str, Any]) -> str:
    from brjarvis.actions.proactive_listener import get_proactive_listener
    listener = get_proactive_listener()
    interval = int(args.get("poll_interval") or 30)
    return listener.start(poll_interval=interval)


@register_tool(
    name="stop_multichannel_listener",
    description="Stop the proactive background listener.",
    parameters={"type": "object", "properties": {}, "required": []}
)
def stop_multichannel_listener_action(args: Dict[str, Any]) -> str:
    from brjarvis.actions.proactive_listener import get_proactive_listener
    listener = get_proactive_listener()
    return listener.stop()


@register_tool(
    name="get_pending_channel_actions",
    description="Retrieve all unhandled incoming Email and WhatsApp messages requiring user opinion or approval.",
    parameters={"type": "object", "properties": {}, "required": []}
)
def get_pending_channel_actions_action(args: Dict[str, Any]) -> str:
    import json
    from brjarvis.actions.proactive_listener import get_proactive_listener
    listener = get_proactive_listener()
    return json.dumps({
        "status": listener.get_status(),
        "pending_actions": listener.pending_actions
    }, indent=2)


@register_tool(
    name="respond_channel_action",
    description="Execute user approval decision ('reply', 'add_to_calendar', or 'dismiss') for a pending message item.",
    parameters={
        "type": "object",
        "properties": {
            "item_id": {"type": "string", "description": "The unique message ID from pending actions list"},
            "decision": {"type": "string", "description": "'reply', 'add_to_calendar', or 'dismiss'"},
            "custom_reply": {"type": "string", "description": "Optional custom message text for reply"},
            "event_title": {"type": "string", "description": "Optional custom title for calendar event"},
            "event_date": {"type": "string", "description": "Optional date string for calendar event (e.g., 'tomorrow')"},
            "event_time": {"type": "string", "description": "Optional time string for calendar event (e.g., '3:00 PM')"}
        },
        "required": ["item_id", "decision"]
    }
)
def respond_channel_action_action(args: Dict[str, Any]) -> str:
    import json
    from brjarvis.actions.channel_action_dispatcher import get_channel_action_dispatcher
    dispatcher = get_channel_action_dispatcher()
    
    item_id = str(args.get("item_id") or "").strip()
    decision = str(args.get("decision") or "").strip()
    custom_reply = args.get("custom_reply")
    
    event_details = {}
    if args.get("event_title"):
        event_details["title"] = args.get("event_title")
    if args.get("event_date"):
        event_details["date"] = args.get("event_date")
    if args.get("event_time"):
        event_details["time"] = args.get("event_time")

    res = dispatcher.process_user_decision(
        item_id=item_id,
        decision=decision,
        custom_reply=custom_reply,
        event_details=event_details if event_details else None
    )
    return json.dumps(res, indent=2)
