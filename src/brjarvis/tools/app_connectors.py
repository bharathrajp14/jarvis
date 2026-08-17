# tools/app_connectors.py — JARVIS MK37 App Connectors (Gmail, Notion, GitHub, Calendar, Slack)
"""
App Connectors for external productivity tools and cloud platforms.
Supports Gmail, Notion, GitHub, Google Calendar, and Slack via ConnectorHub.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .registry import register_tool
from brjarvis.connectors.hub import get_hub

logger = logging.getLogger("JARVIS.AppConnectors")


# ── GMAIL CONNECTORS ──────────────────────────────────────────────────────────

@register_tool(
    name="gmail_list_unread",
    description="List unread emails from Gmail inbox with subject, sender, and snippet.",
    parameters={
        "type": "object",
        "properties": {
            "max_results": {"type": "integer", "description": "Maximum number of unread emails to retrieve (default: 5)"}
        },
        "required": []
    }
)
def gmail_list_unread(max_results: int = 5, *args, **kwargs) -> str:
    """List unread emails from Gmail inbox."""
    if isinstance(max_results, dict):
        max_results = max_results.get("max_results", 5)
    elif len(args) > 0 and isinstance(args[0], dict):
        max_results = args[0].get("max_results", max_results)

    try:
        max_results = int(max_results)
    except (ValueError, TypeError):
        max_results = 5

    hub = get_hub()
    return hub.call("gmail", "list_unread", {"limit": max_results})


@register_tool(
    name="gmail_send_email",
    description="Draft or send an email via Gmail connector.",
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
def gmail_send_email(to: str, subject: str = "", body: str = "", *args, **kwargs) -> str:
    """Send or draft an email via Gmail connector."""
    if isinstance(to, dict):
        subject = to.get("subject", subject)
        body = to.get("body", body)
        to = to.get("to", "")

    hub = get_hub()
    return hub.call("gmail", "send_email", {"to": to, "subject": subject, "body": body})


# ── NOTION CONNECTORS ─────────────────────────────────────────────────────────

@register_tool(
    name="notion_search_pages",
    description="Search Notion workspace for pages, databases, or documentation notes.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for Notion workspace"}
        },
        "required": ["query"]
    }
)
def notion_search_pages(query: str = "", *args, **kwargs) -> str:
    """Search Notion workspace for pages and databases."""
    if isinstance(query, dict):
        query = query.get("query", "")
    elif args and isinstance(args[0], str):
        query = args[0]

    hub = get_hub()
    return hub.call("notion", "search", {"query": query})


@register_tool(
    name="notion_create_page",
    description="Create a new page in a Notion database or workspace root.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title of the new Notion page"},
            "content": {"type": "string", "description": "Markdown body content of the page"}
        },
        "required": ["title"]
    }
)
def notion_create_page(title: str = "", content: str = "", *args, **kwargs) -> str:
    """Create a new page in Notion workspace."""
    if isinstance(title, dict):
        content = title.get("content", content)
        title = title.get("title", "")
    elif args:
        title = args[0]
        if len(args) > 1:
            content = args[1]

    hub = get_hub()
    return hub.call("notion", "create_page", {"title": title, "content": content})


# ── GITHUB CONNECTORS ─────────────────────────────────────────────────────────

@register_tool(
    name="github_list_prs",
    description="List open Pull Requests or Issues in a GitHub repository.",
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository in format 'owner/repo' (default: 'bharthraj1412/BrJarvis')"}
        },
        "required": []
    }
)
def github_list_prs(repo: str = "bharthraj1412/BrJarvis", *args, **kwargs) -> str:
    """List open PRs in a GitHub repository."""
    if isinstance(repo, dict):
        repo = repo.get("repo", "bharthraj1412/BrJarvis")
    elif args and isinstance(args[0], str):
        repo = args[0]

    parts = repo.strip().split("/")
    if len(parts) == 2:
        owner, repo_name = parts
    else:
        owner, repo_name = "bharthraj1412", repo.strip()

    hub = get_hub()
    return hub.call("github", "list_prs", {"owner": owner, "repo": repo_name})


@register_tool(
    name="github_create_issue",
    description="Create a new issue on GitHub repository.",
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository in format 'owner/repo'"},
            "title": {"type": "string", "description": "Issue title"},
            "body": {"type": "string", "description": "Issue description content"}
        },
        "required": ["repo", "title"]
    }
)
def github_create_issue(repo: str = "", title: str = "", body: str = "", *args, **kwargs) -> str:
    """Create a new issue on GitHub repository."""
    if isinstance(repo, dict):
        title = repo.get("title", title)
        body = repo.get("body", body)
        repo = repo.get("repo", "")

    parts = repo.strip().split("/")
    if len(parts) == 2:
        owner, repo_name = parts
    else:
        owner, repo_name = "bharthraj1412", repo.strip()

    hub = get_hub()
    return hub.call("github", "create_issue", {"owner": owner, "repo": repo_name, "title": title, "body": body})


# ── GOOGLE CALENDAR CONNECTORS ────────────────────────────────────────────────

@register_tool(
    name="calendar_list_events",
    description="List upcoming events and meetings from Google Calendar.",
    parameters={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Number of days ahead to search (default: 7)"}
        },
        "required": []
    }
)
def calendar_list_events(days: int = 7, *args, **kwargs) -> str:
    """List upcoming Google Calendar events."""
    if isinstance(days, dict):
        days = days.get("days", 7)
    elif args and isinstance(args[0], (int, dict)):
        days = args[0] if isinstance(args[0], int) else args[0].get("days", 7)

    hub = get_hub()
    return hub.call("calendar", "list_events", {"days": days})


@register_tool(
    name="calendar_create_event",
    description="Schedule a new meeting or event in Google Calendar.",
    parameters={
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Title/summary of the meeting"},
            "start_time": {"type": "string", "description": "ISO start time e.g. '2026-07-22T16:00:00'"},
            "duration_minutes": {"type": "integer", "description": "Duration in minutes (default: 30)"}
        },
        "required": ["summary", "start_time"]
    }
)
def calendar_create_event(summary: str = "", start_time: str = "", duration_minutes: int = 30, *args, **kwargs) -> str:
    """Schedule a new meeting or event in Google Calendar."""
    if isinstance(summary, dict):
        start_time = summary.get("start_time", start_time)
        duration_minutes = summary.get("duration_minutes", duration_minutes)
        summary = summary.get("summary", "")

    hub = get_hub()
    return hub.call("calendar", "create_event", {"summary": summary, "start_time": start_time, "duration_minutes": duration_minutes})


# ── SLACK CONNECTORS ──────────────────────────────────────────────────────────

@register_tool(
    name="slack_send_message",
    description="Post a message to a Slack or Discord dev channel.",
    parameters={
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "Channel name e.g. '#general'"},
            "message": {"type": "string", "description": "Message text to post"}
        },
        "required": ["channel", "message"]
    }
)
def slack_send_message(channel: str = "", message: str = "", *args, **kwargs) -> str:
    """Post a message to a Slack or Discord dev channel."""
    if isinstance(channel, dict):
        message = channel.get("message", message)
        channel = channel.get("channel", "")

    hub = get_hub()
    return hub.call("slack", "post_message", {"channel": channel, "text": message})
