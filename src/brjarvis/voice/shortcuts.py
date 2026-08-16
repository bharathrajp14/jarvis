# voice/shortcuts.py — Sub-10ms Fast Voice Command Dispatcher for JARVIS MK37
"""
Provides fast-path matching for instant voice command execution without passing through full ReAct loop.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, Optional, Tuple


class VoiceShortcutRegistry:
    """Fast-path Voice Command Registry for instant execution."""

    def __init__(self):
        self._shortcuts: Dict[str, Tuple[re.Pattern, str, Dict]] = {}
        self._register_default_shortcuts()

    def register(self, key: str, pattern: str, tool_name: str, args: dict):
        self._shortcuts[key] = (re.compile(pattern, re.IGNORECASE), tool_name, args)

    def _register_default_shortcuts(self):
        self.register(
            "stop_speech",
            r"^(stop speaking|be quiet|shut up|silence|stop talking)$",
            "stop_speech",
            {}
        )
        self.register(
            "system_health",
            r"^(system health|system status|check system|computer status)$",
            "system_diagnostic",
            {"aspect": "cpu_ram"}
        )
        self.register(
            "screenshot",
            r"^(take screenshot|capture screen|screen shot)$",
            "take_screenshot",
            {}
        )
        self.register(
            "open_browser",
            r"^(open browser|open chrome|launch browser)$",
            "open_app",
            {"app_name": "chrome"}
        )
        self.register(
            "open_terminal",
            r"^(open terminal|open cmd|launch terminal|open powershell)$",
            "open_app",
            {"app_name": "powershell"}
        )

    def match(self, spoken_text: str) -> Optional[Tuple[str, dict]]:
        text = spoken_text.strip()
        for key, (pattern, tool_name, args) in self._shortcuts.items():
            if pattern.search(text):
                return tool_name, args
        return None


_SHORTCUTS = VoiceShortcutRegistry()


def match_voice_shortcut(spoken_text: str) -> Optional[Tuple[str, dict]]:
    """Match transcript against voice shortcut rules."""
    return _SHORTCUTS.match(spoken_text)
