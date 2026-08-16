# actions/custom_commands.py — JARVIS MK37 Custom Commands Engine
"""
User-defined custom commands, aliases, replies, and variables.
Allows users to automate chains of actions (speak, open url, open app, run shell command, etc.)
using voice or CLI text.
"""
from __future__ import annotations

import logging
import json
import os
import re
import subprocess
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

_CONFIG_PATH = Path("config/custom_commands.json")


class CustomCommandEngine:
    """Engine to load, match, and execute user-defined custom commands."""

    def __init__(self):
        self.commands: list[dict] = []
        self.startup_commands: list[dict] = []
        self.load_commands()

    def load_commands(self):
        """Load custom commands and startup routines from config file."""
        if not _CONFIG_PATH.parent.exists():
            _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        if not _CONFIG_PATH.exists():
            # Create default empty template
            self.commands = []
            self.startup_commands = []
            self.save_commands()
            return

        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            self.commands = data.get("commands", [])
            self.startup_commands = data.get("startup_commands", [])
        except Exception as e:
            logger.warning(f"[CustomCommands] Load error: {e}")
            self.commands = []
            self.startup_commands = []

    def save_commands(self):
        """Save the current custom commands to config file."""
        try:
            data = {
                "commands": self.commands,
                "startup_commands": self.startup_commands,
            }
            _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    def match(self, text: str) -> tuple[dict, dict] | None:
        """
        Match user input text against triggers and aliases.
        Supports variable extraction (e.g. "search google for $QUERY" matches "search google for python tips").

        Returns:
            tuple (command_dict, extracted_variables) or None
        """
        clean_text = text.lower().strip()

        for cmd in self.commands:
            triggers = [cmd["trigger"]] + cmd.get("aliases", [])
            for trigger in triggers:
                # Convert trigger to regex pattern for variable capture
                # e.g., "search google for $QUERY" -> "^search google for (.*)$"
                pattern_str = "^" + re.escape(trigger.lower()) + "$"
                # Replace variable names like \$query with a regex capture group (.*)
                variables_in_trigger = re.findall(r"\$[A-Za-z0-9_]+", trigger)
                for var in variables_in_trigger:
                    pattern_str = pattern_str.replace(re.escape(var.lower()), r"(.*)")

                try:
                    match = re.match(pattern_str, clean_text)
                    if match:
                        # Extract variable values
                        extracted = {}
                        for i, val in enumerate(match.groups()):
                            var_name = variables_in_trigger[i]
                            extracted[var_name] = val.strip()
                        return cmd, extracted
                except Exception:
                    # If regex compilation fails, fallback to simple match
                    if clean_text == trigger.lower():
                        return cmd, {}

        return None

    def execute(self, cmd: dict, variables: dict, speak_callback=None) -> str:
        """Execute a matched command chain."""
        actions = cmd.get("actions", [])
        if not actions:
            return "No actions defined for this command."

        results = []
        for action in actions:
            action_type = action.get("type", "").lower()
            content = action.get("text", action.get("url", action.get("name", action.get("cmd", ""))))

            # Substitute variables
            for var_name, var_val in variables.items():
                content = content.replace(var_name, var_val)
                content = content.replace(var_name.upper(), var_val)

            try:
                if action_type == "speak":
                    if speak_callback:
                        speak_callback(content)
                    else:
                        logger.info(f"[CustomCommands] Speak: {content}")
                    results.append(f"Spoke: {content}")

                elif action_type == "open_url":
                    webbrowser.open(content)
                    results.append(f"Opened URL: {content}")

                elif action_type == "open_app":
                    from actions.open_app import open_app
                    open_app(parameters={"app_name": content})
                    results.append(f"Opened App: {content}")

                elif action_type == "run_command":
                    # Raw shell execution is intentionally opt-in.
                    allow_unsafe_shell = os.environ.get("JARVIS_ALLOW_UNSAFE_SHELL", "false").strip().lower() in {
                        "1", "true", "yes", "on"
                    }
                    if not allow_unsafe_shell:
                        results.append("Action 'run_command' blocked by policy. Set JARVIS_ALLOW_UNSAFE_SHELL=true to allow.")
                        continue

                    if os.name == "nt":
                        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", content]
                    else:
                        cmd = ["/bin/bash", "-lc", content] if Path("/bin/bash").exists() else ["/bin/sh", "-lc", content]
                    subprocess.Popen(cmd)
                    results.append(f"Ran command: {content}")

                elif action_type == "press_keys":
                    import pyautogui
                    pyautogui.write(content)
                    results.append(f"Typed keys: {content}")

                elif action_type == "hotkey":
                    import pyautogui
                    pyautogui.hotkey(*[k.strip() for k in content.split("+")])
                    results.append(f"Pressed hotkey: {content}")

            except Exception as e:
                results.append(f"Action '{action_type}' failed: {e}")

        return "\n".join(results)

    def add_command(self, trigger: str, actions: list[dict], aliases: list[str] = None) -> str:
        """Add a new custom command dynamically."""
        # Check if trigger already exists
        for cmd in self.commands:
            if cmd["trigger"].lower() == trigger.lower():
                cmd["actions"] = actions
                if aliases is not None:
                    cmd["aliases"] = aliases
                self.save_commands()
                return f"Updated custom command: '{trigger}'"

        self.commands.append({
            "trigger": trigger,
            "aliases": aliases or [],
            "actions": actions,
            "variables": {},
        })
        self.save_commands()
        return f"Added custom command: '{trigger}'"

    def delete_command(self, trigger: str) -> str:
        """Delete a custom command by trigger name."""
        for i, cmd in enumerate(self.commands):
            if cmd["trigger"].lower() == trigger.lower():
                self.commands.pop(i)
                self.save_commands()
                return f"Deleted custom command: '{trigger}'"
        return f"Custom command '{trigger}' not found."


# Singleton instance
custom_command_engine = CustomCommandEngine()
