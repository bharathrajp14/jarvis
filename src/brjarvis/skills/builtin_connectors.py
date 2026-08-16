# skills/builtin_connectors.py — Built-in App Connector Skills for BR-JARVIS MK37
"""
Built-in connector skills for Gmail, WhatsApp, Telegram, Google Calendar, Notion, GitHub, Slack, and Microsoft 365.
"""
from __future__ import annotations

from .loader import SkillDef

CONNECTOR_SKILLS: list[SkillDef] = [
    SkillDef(
        name="gmail_assistant",
        description="Inspect inbox, read unread messages, compose and send emails via Gmail connector.",
        triggers=["/gmail", "/email", "check emails", "read gmail", "send email", "check unread messages"],
        tools=["gmail_send", "gmail_reply", "send_email", "gmail_list_unread", "get_gmail_auth_status", "schedule_email"],
        prompt="""
You are the BR-JARVIS Executive Communications Specialist.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Check Gmail auth status via `get_gmail_auth_status`.
2. If unread messages are requested, use `gmail_list_unread` to retrieve subject headers and sender info.
3. If sending or replying to an email, format a clear professional body and dispatch using `gmail_send`, `gmail_reply`, or `send_email`.
4. Report email status, recipient, and message ID.
""",
        file_path="builtin:gmail_assistant",
        category="productivity",
        domain="Email Communication",
        when_to_use="When the user asks to check, send, compose, or reply to emails in Gmail.",
        source="builtin",
        user_invocable=True
    ),
    SkillDef(
        name="whatsapp_assistant",
        description="Send instant WhatsApp messages, schedule reminders, and broadcast updates.",
        triggers=["/whatsapp", "/wa", "send whatsapp", "whatsapp message"],
        tools=["send_whatsapp", "schedule_whatsapp_message", "manage_whatsapp_contacts"],
        prompt="""
You are the BR-JARVIS WhatsApp Dispatch Specialist.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Identify the recipient name/number and message payload from $ARGUMENTS.
2. If the contact name is provided, resolve contact information using `manage_whatsapp_contacts`.
3. If immediate dispatch is requested, call `send_whatsapp(recipient=..., message=...)`.
4. If future scheduled delivery is requested, call `schedule_whatsapp_message(recipient=..., message=..., scheduled_time=...)`.
5. Confirm delivery or scheduling details to the user.
""",
        file_path="builtin:whatsapp_assistant",
        category="productivity",
        domain="Instant Messaging",
        when_to_use="When the user wants to send or schedule WhatsApp messages.",
        source="builtin",
        user_invocable=True
    ),
    SkillDef(
        name="telegram_bot_assistant",
        description="Send Telegram alerts, monitor updates, and manage chat broadcasts.",
        triggers=["/telegram", "/tg", "send telegram", "telegram alert"],
        tools=["send_telegram", "schedule_telegram_message", "telegram_get_updates", "telegram_bot_info", "manage_telegram_contacts"],
        prompt="""
You are the BR-JARVIS Telegram Automation Specialist.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Check bot configuration with `telegram_bot_info` or retrieve latest messages with `telegram_get_updates`.
2. Format the message markdown and dispatch using `send_telegram(chat_id=..., message=...)`.
3. Confirm transmission receipt and delivery timestamp.
""",
        file_path="builtin:telegram_bot_assistant",
        category="productivity",
        domain="Instant Messaging",
        when_to_use="When the user wants to interact with Telegram or broadcast Telegram messages.",
        source="builtin",
        user_invocable=True
    ),
    SkillDef(
        name="calendar_meeting_scheduler",
        description="Inspect calendar schedule, detect conflicts, and create/manage meetings.",
        triggers=["/calendar", "/schedule", "check schedule", "upcoming meetings", "schedule meeting", "create event"],
        tools=["calendar_list_events", "calendar_create_event", "delete_calendar_event", "search_calendar_events"],
        prompt="""
You are the BR-JARVIS Executive Scheduler.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Use `calendar_list_events` or `search_calendar_events` to retrieve upcoming appointments and check for timing conflicts.
2. If creating a new meeting or event, call `calendar_create_event(title=..., start_time=..., end_time=..., description=...)`.
3. Confirm event title, time slot, and calendar sync status.
""",
        file_path="builtin:calendar_meeting_scheduler",
        category="productivity",
        domain="Calendar & Scheduling",
        when_to_use="When the user asks about their schedule or booking calendar events.",
        source="builtin",
        user_invocable=True
    ),
    SkillDef(
        name="notion_workspace_manager",
        description="Search, create, and organize documentation pages and database entries in Notion.",
        triggers=["/notion", "search notion", "create notion page", "notion notes"],
        tools=["notion_search_pages", "notion_create_page"],
        prompt="""
You are the BR-JARVIS Workspace Architect.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Use `notion_search_pages` to verify if a matching page or database exists.
2. If creating new documentation, call `notion_create_page` with well-formatted markdown content and title.
3. Return the created page confirmation and structure summary.
""",
        file_path="builtin:notion_workspace_manager",
        category="productivity",
        domain="Workspace Knowledge",
        when_to_use="When the user requests searching, creating, or editing Notion pages.",
        source="builtin",
        user_invocable=True
    ),
    SkillDef(
        name="github_workflow_auditor",
        description="Audit open Pull Requests and Issues, analyze CI logs, and create issues in GitHub.",
        triggers=["/github", "/gh", "check prs", "list github issues", "audit repository"],
        tools=["github_list_prs", "github_create_issue", "run_code"],
        prompt="""
You are the BR-JARVIS Lead Code Auditor & Release Engineer.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Use `github_list_prs` to inspect open Pull Requests.
2. Analyze diffs for security vulnerabilities, test gaps, and merge conflicts.
3. If issues need to be filed, invoke `github_create_issue(title=..., body=...)`.
4. Summarize repository health and next actions.
""",
        file_path="builtin:github_workflow_auditor",
        category="engineering",
        domain="Version Control",
        when_to_use="When the user asks to check GitHub PRs, issues, or review open pull requests.",
        source="builtin",
        user_invocable=True
    ),
    SkillDef(
        name="slack_channel_broadcaster",
        description="Post automated build notifications, release logs, and dev digests to Slack channels.",
        triggers=["/slack", "post to slack", "send slack message", "notify channel"],
        tools=["slack_send_message"],
        prompt="""
You are the BR-JARVIS Communications Dispatcher.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Format a clean markdown announcement or status report.
2. Call `slack_send_message` with channel and text.
3. Confirm message transmission.
""",
        file_path="builtin:slack_channel_broadcaster",
        category="productivity",
        domain="Team Chat",
        when_to_use="When the user asks to post or broadcast messages to Slack.",
        source="builtin",
        user_invocable=True
    ),
    SkillDef(
        name="ms365_workspace_manager",
        description="Launch and interact with Microsoft 365 / Office Online web apps (Word, Excel, PowerPoint, Outlook).",
        triggers=["/ms365", "/office365", "open office online", "open word online", "open excel online"],
        tools=["ms365_control", "browser_open_url", "browser_click", "browser_type"],
        prompt="""
You are the BR-JARVIS Office Online Specialist.

## Task Goal
$ARGUMENTS

## Execution Protocol
1. Use `ms365_control` to launch Word Online, Excel Online, PowerPoint Online, or Outlook.
2. Use interactive browser tools (`browser_click`, `browser_type`) to inspect or edit documents online.
3. Confirm document session state.
""",
        file_path="builtin:ms365_workspace_manager",
        category="productivity",
        domain="Office Automation",
        when_to_use="When the user asks to open or work with Microsoft 365 / Office Online.",
        source="builtin",
        user_invocable=True
    ),
]


def load_builtin_connector_skills() -> list[SkillDef]:
    return CONNECTOR_SKILLS
