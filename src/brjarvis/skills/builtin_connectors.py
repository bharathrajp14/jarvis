# skills/builtin_connectors.py — Built-in App Connector Skills for JARVIS MK37
"""
Built-in skill definitions for Gmail, Notion, GitHub, Google Calendar, and Slack.
"""
from __future__ import annotations

from .loader import SkillDef

CONNECTOR_SKILLS: list[SkillDef] = [
    SkillDef(
        name="gmail_assistant",
        description="Check unread Gmail messages, extract key directives, and generate executive digests.",
        triggers=["/gmail", "check emails", "read gmail", "check unread messages"],
        tools=["gmail_send", "gmail_reply", "browser_open_url", "browser_click", "browser_type"],
        prompt="""
You are the JARVIS Executive Communications Specialist.
Execute the following workflow:
1. Use `gmail_send` or `gmail_reply` to compose, send, or reply to emails online in Gmail.
2. Use `browser_open_url` to inspect Gmail inbox or thread details when requested.
""",
        file_path="builtin:gmail_assistant",
        when_to_use="When the user asks to check, send, compose, or reply to emails in Gmail.",
        source="builtin"
    ),
    SkillDef(
        name="notion_workspace_manager",
        description="Search, create, and organize workspace pages and database entries in Notion.",
        triggers=["/notion", "search notion", "create notion page", "notion notes"],
        tools=["notion_search_pages", "notion_create_page"],
        prompt="""
You are the JARVIS Workspace Architect.
Execute the following workflow:
1. Use `notion_search_pages` to check if a relevant page or database exists.
2. If requested by the user, use `notion_create_page` to document meeting notes, task cards, or system specs.
""",
        file_path="builtin:notion_workspace_manager",
        when_to_use="When the user requests searching, creating, or editing Notion pages.",
        source="builtin"
    ),
    SkillDef(
        name="github_workflow_auditor",
        description="Audit open Pull Requests and Issues in GitHub repository.",
        triggers=["/github", "check prs", "list github issues", "audit repository"],
        tools=["github_list_prs", "github_create_issue"],
        prompt="""
You are the JARVIS Lead Code Auditor & Release Engineer.
Execute the following workflow:
1. Use `github_list_prs` to inspect active Pull Requests.
2. Identify security vulnerabilities, performance bottlenecks, or test gaps.
3. Summarize open PRs and suggest actionable refactoring steps.
""",
        file_path="builtin:github_workflow_auditor",
        when_to_use="When the user asks to check GitHub PRs, issues, or review open pull requests.",
        source="builtin"
    ),
    SkillDef(
        name="calendar_meeting_scheduler",
        description="Inspect Google Calendar schedule and organize meetings.",
        triggers=["/calendar", "check schedule", "upcoming meetings", "schedule event"],
        tools=["calendar_list_events", "calendar_create_event"],
        prompt="""
You are the JARVIS Executive Scheduler.
Execute the following workflow:
1. Use `calendar_list_events` to retrieve upcoming meetings and events.
2. Check for schedule conflicts or open time slots.
3. If requested, call `calendar_create_event` to schedule new meetings.
""",
        file_path="builtin:calendar_meeting_scheduler",
        when_to_use="When the user asks about their calendar schedule or scheduling meetings.",
        source="builtin"
    ),
    SkillDef(
        name="slack_channel_broadcaster",
        description="Post automated build notifications, release logs, and dev digests to Slack channels.",
        triggers=["/slack", "post to slack", "send slack message", "notify channel"],
        tools=["slack_send_message"],
        prompt="""
You are the JARVIS Communications Dispatcher.
Execute the following workflow:
1. Format a clean markdown announcement or status report.
2. Call `slack_send_message` to post the announcement to the target channel.
""",
        file_path="builtin:slack_channel_broadcaster",
        when_to_use="When the user asks to post or broadcast messages to Slack/Discord.",
        source="builtin"
    ),
    SkillDef(
        name="ms365_workspace_manager",
        description="Launch and interact with Microsoft 365 / Office Online web apps (Word, Excel, PowerPoint, Outlook).",
        triggers=["/ms365", "/office365", "open office online", "open word online", "open excel online"],
        tools=["ms365_control", "browser_open_url", "browser_click", "browser_type"],
        prompt="""
You are the JARVIS Office Online Specialist.
Execute the following workflow:
1. Use `ms365_control` to launch Word Online, Excel Online, PowerPoint Online, or Outlook.
2. Use interactive browser tools (`browser_click`, `browser_type`) to edit documents online.
""",
        file_path="builtin:ms365_workspace_manager",
        when_to_use="When the user asks to open or work with Microsoft 365 / Office Online.",
        source="builtin"
    ),
]


def load_builtin_connector_skills() -> list[SkillDef]:
    return CONNECTOR_SKILLS
