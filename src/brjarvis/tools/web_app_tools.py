# tools/web_app_tools.py — JARVIS MK37 Online Web App Tool Registrations
"""
Registered tool wrappers for Gmail and Microsoft 365 / Office Online interactions.
"""
from __future__ import annotations

from .registry import register_tool, _run_async
from brjarvis.actions.web_app_controller import (
    gmail_compose_and_send_async,
    gmail_search_and_reply_async,
    ms365_open_app_async,
)


@register_tool(
    name="gmail_send",
    description="Compose and send an email via Gmail online in the browser.",
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body content"}
        },
        "required": ["to", "subject", "body"]
    }
)
def gmail_send(args: dict) -> str:
    """Compose and send Gmail email."""
    if isinstance(args, str):
        return "ERROR: 'gmail_send' expects a JSON dictionary with 'to', 'subject', and 'body'."
    to = str(args.get("to") or args.get("recipient") or args.get("target_email") or args.get("email") or "").strip()
    subject = str(args.get("subject") or args.get("title") or args.get("topic") or "No Subject").strip()
    body = str(args.get("body") or args.get("message") or args.get("content") or args.get("text") or "").strip()
    if not to or not body:
        return "ERROR: 'to' (recipient) and 'body' parameters are required for gmail_send."
    return _run_async(gmail_compose_and_send_async(to, subject, body))


@register_tool(
    name="gmail_reply",
    description="Search Gmail inbox for an email thread and send a reply message.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term or sender name/subject to locate email"},
            "reply_text": {"type": "string", "description": "Reply text message body"}
        },
        "required": ["query", "reply_text"]
    }
)
def gmail_reply(args: dict) -> str:
    """Search Gmail thread and send reply."""
    if isinstance(args, str):
        return "ERROR: 'gmail_reply' expects a JSON dictionary."
    query = str(args.get("query") or args.get("q") or args.get("search") or args.get("target") or "").strip()
    reply_text = str(args.get("reply_text") or args.get("message") or args.get("text") or args.get("body") or "").strip()
    if not query or not reply_text:
        return "ERROR: 'query' and 'reply_text' parameters are required for gmail_reply."
    return _run_async(gmail_search_and_reply_async(query, reply_text))


@register_tool(
    name="ms365_control",
    description="Launch and interact with Microsoft 365 / Office Online web apps (Word, Excel, PowerPoint, Outlook, Home).",
    parameters={
        "type": "object",
        "properties": {
            "app": {"type": "string", "description": "App name: 'word', 'excel', 'powerpoint', 'outlook', or 'home'"}
        },
        "required": ["app"]
    }
)
def ms365_control(args: dict) -> str:
    """Open Microsoft 365 web app."""
    if isinstance(args, str):
        app = args.strip()
    else:
        app = str(args.get("app") or args.get("name") or args.get("application") or "home").strip()
    return _run_async(ms365_open_app_async(app))
