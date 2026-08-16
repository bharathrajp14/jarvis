# tools/gmail_auth_tools.py — BR-Jarvis Gmail Login & Auth Tools Plugin
"""
Gmail Authentication Tools Plugin for JARVIS.
Exposes tools for Gmail sign-in, authentication status checking, and account sign-out.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from .registry import register_tool
from actions.gmail_auth import get_gmail_auth_manager


@register_tool(
    name="gmail_login",
    description="Log in to Gmail. Mode 'browser' opens Google Sign-In page in browser. Mode 'credentials' saves email and Google App Password for automated email access.",
    parameters={
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["browser", "credentials"], "description": "Login mode: 'browser' for interactive sign-in, or 'credentials' for App Password"},
            "email": {"type": "string", "description": "Gmail email address (required for credentials mode)"},
            "app_password": {"type": "string", "description": "16-character Google App Password (required for credentials mode)"}
        },
        "required": ["mode"]
    }
)
def tool_gmail_login(args: dict) -> str:
    """Initiate Gmail sign-in or save credentials."""
    mode = str(args.get("mode", "browser")).strip().lower()
    mgr = get_gmail_auth_manager()

    if mode == "browser":
        return mgr.start_browser_login()

    elif mode in ("credentials", "app_password"):
        email = str(args.get("email", "")).strip()
        pwd = str(args.get("app_password", "")).strip()

        if not email or not pwd:
            return "Error: 'email' and 'app_password' are required for credentials mode."

        return mgr.configure_credentials(email_address=email, app_password=pwd)

    return f"Unknown login mode '{mode}'. Supported modes: 'browser', 'credentials'."


@register_tool(
    name="get_gmail_auth_status",
    description="Check whether a Gmail account is currently logged in, showing active email address and authentication method.",
    parameters={
        "type": "object",
        "properties": {}
    }
)
def tool_get_gmail_auth_status(args: dict) -> str:
    """Check Gmail authentication status."""
    mgr = get_gmail_auth_manager()
    status = mgr.get_status()

    if status["logged_in"]:
        email_str = f" as '{status['email']}'" if status['email'] else ""
        return f"🔒 Gmail Status: LOGGED IN{email_str} (Auth Method: {status['auth_method']})."

    return "🔒 Gmail Status: NOT LOGGED IN. Use 'gmail_login' to sign in."


@register_tool(
    name="gmail_logout",
    description="Sign out of Gmail and clear stored credentials and session tokens from local storage.",
    parameters={
        "type": "object",
        "properties": {}
    }
)
def tool_gmail_logout(args: dict) -> str:
    """Sign out of Gmail."""
    mgr = get_gmail_auth_manager()
    return mgr.logout()
