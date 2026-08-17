# actions/channel_action_dispatcher.py — Interactive Action Dispatcher for JARVIS Multi-Channel Listener
"""
Dispatches user-approved actions (Reply via Email/WhatsApp, Add to Calendar)
from proactive channel listener.
"""
from __future__ import annotations

import datetime
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("JARVIS.ChannelActionDispatcher")


class ChannelActionDispatcher:
    """Handles user approval choices for queued proactive channel messages."""

    def __init__(self, listener: Optional[Any] = None):
        self._listener = listener

    def process_user_decision(
        self,
        item_id: str,
        decision: str,
        custom_reply: Optional[str] = None,
        event_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process user's decision for a pending item.

        Args:
            item_id: The unique message ID
            decision: "reply" | "add_to_calendar" | "dismiss"
            custom_reply: Optional custom message text to send
            event_details: Optional calendar event dict (title, start_time, end_time)

        Returns:
            Status result dictionary
        """
        listener = self._listener
        if listener is None:
            from brjarvis.actions.proactive_listener import get_proactive_listener
            listener = get_proactive_listener()

        # Find target pending item
        target_item = None
        for item in listener.pending_actions:
            if item["id"] == item_id:
                target_item = item
                break

        if not target_item:
            return {"success": False, "error": f"Item '{item_id}' not found in pending queue."}

        decision = decision.lower().strip()

        if decision == "dismiss":
            listener.pending_actions.remove(target_item)
            logger.info("Pending item %s dismissed by user.", item_id)
            return {"success": True, "action": "dismissed", "message": "Item dismissed."}

        elif decision == "reply":
            result = self._execute_reply(target_item, custom_reply)
            listener.pending_actions.remove(target_item)
            return result

        elif decision == "add_to_calendar":
            result = self._execute_add_to_calendar(target_item, event_details)
            listener.pending_actions.remove(target_item)
            return result

        else:
            return {"success": False, "error": f"Invalid decision '{decision}'. Use 'reply', 'add_to_calendar', or 'dismiss'."}

    def _execute_reply(self, item: Dict[str, Any], custom_reply: Optional[str]) -> Dict[str, Any]:
        channel = item["channel"]
        sender = item["sender"]
        snippet = item["snippet"]

        reply_text = custom_reply or f"Hello {sender}, thank you for your message regarding '{snippet[:40]}...'. I have received it and will follow up shortly."

        if channel == "EMAIL":
            try:
                from brjarvis.actions.smart_email_sender import get_smart_email_sender
                sender_engine = get_smart_email_sender()
                res = sender_engine.send_email(to_address=sender, subject=f"Re: {item.get('subject', 'Message')}", body=reply_text)
                return {"success": True, "action": "reply_email", "result": res}
            except Exception as e:
                logger.error("Email reply error: %s", e)
                return {"success": False, "error": f"Failed to send email reply: {e}"}

        elif channel == "WHATSAPP":
            try:
                from brjarvis.actions.whatsapp_automation import get_whatsapp_automation
                wa = get_whatsapp_automation()
                res = wa.send_message(recipient=sender, message=reply_text)
                return {"success": True, "action": "reply_whatsapp", "result": res}
            except Exception as e:
                logger.error("WhatsApp reply error: %s", e)
                return {"success": False, "error": f"Failed to send WhatsApp reply: {e}"}

        return {"success": False, "error": f"Unsupported channel '{channel}' for reply."}

    def _execute_add_to_calendar(self, item: Dict[str, Any], custom_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        entities = item.get("entities", {})
        title = (custom_details or {}).get("title") or entities.get("title") or f"Meeting with {item['sender']}"
        date_str = (custom_details or {}).get("date") or entities.get("date") or "tomorrow"
        time_str = (custom_details or {}).get("time") or entities.get("time") or "10:00 AM"

        try:
            from brjarvis.actions.calendar_engine import get_calendar_engine
            cal = get_calendar_engine()
            res = cal.create_event(title=title, date_str=date_str, time_str=time_str)
            return {"success": True, "action": "add_to_calendar", "result": res}
        except Exception as e:
            logger.error("Calendar creation error: %s", e)
            return {"success": False, "error": f"Failed to create calendar event: {e}"}


_dispatcher_instance = ChannelActionDispatcher()


def get_channel_action_dispatcher() -> ChannelActionDispatcher:
    return _dispatcher_instance
