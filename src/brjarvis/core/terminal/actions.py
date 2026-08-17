# core/terminal/actions.py — Focus Model & Semantic Action Registry for BR JARVIS MK41
"""
Focus Management & Semantic Action Router.
Maps normalized mouse clicks, double-clicks, and keyboard shortcuts to safe semantic actions
with full keyboard-mouse parity (scroll, tool toggle, URL opening, file jumping, permissions).
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import webbrowser
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("JARVIS.Actions")


class FocusState(str, Enum):
    FOCUS_PROMPT = "prompt"
    FOCUS_TRANSCRIPT = "transcript"
    FOCUS_DIALOG = "dialog"
    FOCUS_MENU = "menu"
    FOCUS_TOOL_RESULT = "tool_result"


class FocusManager:
    """Tracks currently focused UI pane and directs keyboard/mouse events."""

    def __init__(self, initial_focus: FocusState = FocusState.FOCUS_PROMPT):
        self.current_focus: FocusState = initial_focus

    def set_focus(self, focus: FocusState) -> None:
        self.current_focus = focus

    @property
    def is_prompt_focused(self) -> bool:
        return self.current_focus == FocusState.FOCUS_PROMPT

    @property
    def is_dialog_focused(self) -> bool:
        return self.current_focus == FocusState.FOCUS_DIALOG


class ActionRegistry:
    """
    Central action registry executing safe, semantic UI and OS interactions.
    Never executes arbitrary unsanitized shell commands from clicks.
    """

    _SAFE_URL_RE = re.compile(r"^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+$")

    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._register_default_actions()

    def register(self, action_name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a handler for a semantic action."""
        self._handlers[action_name] = handler

    def execute(self, action_name: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Dispatch a semantic action with args."""
        handler = self._handlers.get(action_name)
        if not handler:
            logger.debug("No handler registered for action: %s", action_name)
            return None
        try:
            return handler(args or {})
        except Exception as e:
            logger.error("Error executing action '%s': %s", action_name, e)
            return None

    def _register_default_actions(self) -> None:
        """Register standard safe handlers."""
        self.register("link:open", self._action_open_link)
        self.register("file:open", self._action_open_file)

    @classmethod
    def _action_open_link(cls, args: Dict[str, Any]) -> bool:
        """Safely open validated HTTP/HTTPS URL in user's default browser."""
        url = str(args.get("url", "")).strip()
        if not url or not cls._SAFE_URL_RE.match(url):
            logger.warning("Blocked invalid or dangerous URL: %s", url)
            return False
        try:
            return webbrowser.open(url, new=2)
        except Exception as e:
            logger.warning("Could not open browser for URL '%s': %s", url, e)
            return False

    @classmethod
    def _action_open_file(cls, args: Dict[str, Any]) -> bool:
        """
        Safely open file at optional line number in user's configured editor.
        Format in args: path='src/app.py', line=12
        """
        raw_path = str(args.get("path", "")).strip()
        line = args.get("line")

        if not raw_path:
            return False

        # If path is 'path:line', parse it
        if ":" in raw_path and (line is None):
            parts = raw_path.rsplit(":", 1)
            if parts[1].isdigit():
                raw_path = parts[0]
                line = int(parts[1])

        target_file = Path(raw_path).resolve()
        if not target_file.exists():
            logger.warning("File does not exist: %s", target_file)
            return False

        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
        line_num = int(line) if (line is not None and str(line).isdigit()) else None

        try:
            if editor:
                cmd = [editor]
                if line_num and editor in ("code", "cursor", "subl"):
                    cmd.extend(["-g", f"{target_file}:{line_num}"])
                elif line_num and editor in ("vim", "vi", "nvim", "nano"):
                    cmd.extend([f"+{line_num}", str(target_file)])
                else:
                    cmd.append(str(target_file))

                subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            else:
                # Windows os.startfile fallback
                if hasattr(os, "startfile"):
                    os.startfile(str(target_file))  # type: ignore
                    return True
                # macOS open
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(target_file)])
                    return True
                # Linux xdg-open
                else:
                    subprocess.Popen(["xdg-open", str(target_file)])
                    return True
        except Exception as e:
            logger.warning("Could not open file '%s': %s", target_file, e)
            return False
