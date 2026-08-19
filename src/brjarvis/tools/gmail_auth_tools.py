# tools/gmail_auth_tools.py — BR JARVIS Verified Gmail Auth Suite
"""
High-Fidelity Verified Gmail Authentication & Login Suite for BR JARVIS MK40.2 / MK41.
Provides interactive login, App Password configuration, status inspection,
and canonical ToolResult evidence contracts.
"""

from __future__ import annotations

from brjarvis.actions.gmail_auth import get_gmail_auth_manager

from .domain import ToolErrorCode
from .registry import register_tool
from .tool_result import ToolResult


@register_tool(
    name="gmail_login",
    description="Open Gmail in browser or configure automated credentials. Mode 'browser' opens Gmail inbox. Mode 'compose' opens Gmail with compose window. Mode 'credentials' saves email and Google App Password.",
    parameters={
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["browser", "compose", "credentials"],
                "description": "Login mode: 'browser' for inbox, 'compose' for compose window, 'credentials' for App Password",
            },
            "email": {"type": "string", "description": "Gmail address (required for credentials mode)"},
            "app_password": {
                "type": "string",
                "description": "16-character Google App Password (required for credentials mode)",
            },
        },
        "required": ["mode"],
    },
    category="communication",
    risk_level="medium",
    permission_required="EXTERNAL_COMMUNICATION",
    is_read_only=False,
    verification_strategy="READ_BACK_VALUE",
)
def tool_gmail_login(args: dict) -> ToolResult:
    """Initiate Gmail sign-in, inbox opening, or save credentials."""
    mode = str(args.get("mode", "browser")).strip().lower()
    mgr = get_gmail_auth_manager()

    try:
        if mode in ("browser", "inbox", "open"):
            msg = mgr.start_browser_login(compose=False)
            evidence = "Opened Gmail inbox in web browser."
            return ToolResult.success(
                tool_name="gmail_login",
                data={"mode": mode, "status": "browser_opened"},
                output=msg,
                evidence=evidence,
                verified=True,
            )

        elif mode in ("compose", "draft", "new_mail", "new_email"):
            msg = mgr.start_browser_login(compose=True)
            evidence = "Opened Gmail compose window in web browser."
            return ToolResult.success(
                tool_name="gmail_login",
                data={"mode": mode, "status": "compose_opened"},
                output=msg,
                evidence=evidence,
                verified=True,
            )

        elif mode in ("credentials", "app_password"):
            email = str(args.get("email", "")).strip()
            pwd = str(args.get("app_password", "")).strip()

            if not email or not pwd:
                return ToolResult.failed(
                    "gmail_login",
                    ToolErrorCode.INVALID_ARGUMENT,
                    "Parameters 'email' and 'app_password' are required for credentials mode.",
                )

            msg = mgr.configure_credentials(email_address=email, app_password=pwd)
            evidence = f"Configured Google App Password for '{email}'."
            return ToolResult.success(
                tool_name="gmail_login",
                data={"email": email, "auth_method": "app_password"},
                output=msg,
                evidence=evidence,
                verified=True,
                metadata={"email": email},
            )

        else:
            return ToolResult.failed(
                "gmail_login",
                ToolErrorCode.INVALID_ARGUMENT,
                f"Unknown login mode '{mode}'. Allowed: 'browser', 'compose', 'credentials'.",
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="gmail_login",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Gmail login error: {e}",
        )


@register_tool(
    name="get_gmail_auth_status",
    description="Check whether a Gmail account is currently configured or logged in.",
    parameters={
        "type": "object",
        "properties": {},
    },
    category="communication",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_get_gmail_auth_status(args: dict) -> ToolResult:
    """Check Gmail authentication status."""
    try:
        mgr = get_gmail_auth_manager()
        status = mgr.get_status()

        if status.get("logged_in"):
            email_str = f" as '{status['email']}'" if status.get("email") else ""
            evidence = f"Gmail Status: LOGGED IN{email_str} (Auth Method: {status.get('auth_method')})."
        else:
            evidence = "Gmail Status: NOT LOGGED IN."

        return ToolResult.success(
            tool_name="get_gmail_auth_status",
            data=status,
            output=evidence,
            evidence=evidence,
            verified=True,
            metadata=status,
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="get_gmail_auth_status",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to check Gmail status: {e}",
        )


@register_tool(
    name="gmail_logout",
    description="Sign out of Gmail and clear stored credentials and session tokens.",
    parameters={
        "type": "object",
        "properties": {},
    },
    category="communication",
    risk_level="medium",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_gmail_logout(args: dict) -> ToolResult:
    """Sign out of Gmail and clear credentials."""
    try:
        mgr = get_gmail_auth_manager()
        msg = mgr.logout()
        evidence = "Cleared local Gmail configuration and session tokens."
        return ToolResult.success(
            tool_name="gmail_logout",
            data={"logged_out": True},
            output=msg,
            evidence=evidence,
            verified=True,
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="gmail_logout",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error signing out of Gmail: {e}",
        )
