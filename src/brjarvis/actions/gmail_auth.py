# actions/gmail_auth.py — Gmail Login & Authentication Manager for BR-Jarvis
"""
Gmail Login & Authentication Manager for BR-Jarvis.
Supports interactive browser login to Google/Gmail, App Password configuration,
OAuth2 token storage, and session status inspection.
"""
from __future__ import annotations

import os
import json
import logging
import webbrowser
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("JARVIS.GmailAuth")


def _get_config_dir() -> Path:
    cfg_dir = Path.cwd() / ".jarvis"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


class GmailAuthManager:
    """
    Manager for Gmail authentication, login sessions, and credential storage.
    """

    def __init__(self):
        self.config_file = _get_config_dir() / "gmail_config.json"
        self.tokens_file = _get_config_dir() / "gmail_tokens.json"
        self._load_and_sync_env()

    def _load_and_sync_env(self):
        """Sync saved Gmail credentials with process environment variables."""
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                email_addr = data.get("email", "").strip()
                pwd = data.get("app_password", "").strip()

                if email_addr and pwd:
                    os.environ["SMTP_USER"] = email_addr
                    os.environ["SMTP_PASSWORD"] = pwd
                    os.environ["IMAP_USER"] = email_addr
                    os.environ["IMAP_PASSWORD"] = pwd
                    os.environ["GMAIL_ADDRESS"] = email_addr
            except Exception as e:
                logger.error(f"Error reading Gmail config: {e}")

    def start_browser_login(self, target_url: str = "https://mail.google.com", compose: bool = False) -> str:
        """
        Launch Gmail directly in default system browser, opening inbox or compose window.
        """
        dest_url = "https://mail.google.com/mail/u/0/#inbox?compose=new" if compose else target_url
        try:
            webbrowser.open(dest_url)
            if compose:
                return (
                    "🌐 Opened Gmail Compose window in your browser.\n"
                    "You can write and review your email directly in the browser."
                )
            return (
                "🌐 Opened Gmail in your browser.\n"
                "If you are already signed in to Google, your inbox is open. Otherwise, complete sign-in in the browser window."
            )
        except Exception as e:
            return f"Error opening browser for Gmail: {e}"

    def configure_credentials(self, email_address: str, app_password: str) -> str:
        """
        Configure Gmail address and Google App Password for automated email access.
        """
        clean_email = email_address.strip()
        clean_pwd = app_password.strip()

        if not clean_email or not clean_pwd:
            return "Error: Both email address and Google App Password are required."

        try:
            config = {
                "email": clean_email,
                "app_password": clean_pwd,
                "auth_method": "app_password"
            }
            self.config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
            self._load_and_sync_env()

            return f"✅ Gmail login configured successfully for '{clean_email}'."
        except Exception as e:
            return f"Failed to save Gmail credentials: {e}"

    def get_status(self) -> Dict[str, Any]:
        """
        Inspect current Gmail authentication status.
        """
        status: Dict[str, Any] = {
            "logged_in": False,
            "email": None,
            "auth_method": "none",
            "details": "No Gmail account configured or authenticated."
        }

        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                email_addr = data.get("email")
                method = data.get("auth_method", "app_password")

                if email_addr:
                    status["logged_in"] = True
                    status["email"] = email_addr
                    status["auth_method"] = method
                    status["details"] = f"Authenticated via {method} as {email_addr}"
                    return status
            except Exception:
                pass

        if self.tokens_file.exists():
            status["logged_in"] = True
            status["auth_method"] = "oauth2"
            status["details"] = "OAuth2 tokens stored locally."
            return status

        # Check env variables as fallback
        env_email = os.environ.get("GMAIL_ADDRESS") or os.environ.get("SMTP_USER")
        if env_email:
            status["logged_in"] = True
            status["email"] = env_email
            status["auth_method"] = "environment_vars"
            status["details"] = f"Configured via environment variables as {env_email}"

        return status

    def logout(self) -> str:
        """
        Sign out and clear stored Gmail login credentials and tokens.
        """
        cleared = []
        if self.config_file.exists():
            try:
                self.config_file.unlink()
                cleared.append("gmail_config.json")
            except Exception:
                pass

        if self.tokens_file.exists():
            try:
                self.tokens_file.unlink()
                cleared.append("gmail_tokens.json")
            except Exception:
                pass

        # Clear env variables
        for key in ("SMTP_USER", "SMTP_PASSWORD", "IMAP_USER", "IMAP_PASSWORD", "GMAIL_ADDRESS"):
            os.environ.pop(key, None)

        if cleared:
            return f"✅ Gmail account signed out. Removed {', '.join(cleared)}."
        return "No active Gmail login credentials to clear."


# Global singleton instance
_gmail_auth_instance = GmailAuthManager()


def get_gmail_auth_manager() -> GmailAuthManager:
    return _gmail_auth_instance
