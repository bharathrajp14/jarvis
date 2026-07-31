# actions/hotkeys.py — JARVIS MK37 Global Hotkeys System
"""
Registers global keyboard shortcuts using the 'keyboard' module.
Allows users to trigger actions like toggling voice listening,
running clipboard queries, or taking screenshots.
"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback
from pathlib import Path

_CONFIG_PATH = Path("config/hotkeys.json")

_HAS_KEYBOARD = False
try:
    import keyboard
    _HAS_KEYBOARD = True
except ImportError:
    pass


class HotkeyManager:
    """Manages global keyboard hotkeys."""

    def __init__(self, assistant_ref=None):
        self.assistant = assistant_ref
        self.hotkeys: list[dict] = []
        self._listener_thread = None
        self._running = False

    def load_hotkeys(self):
        """Load hotkeys from config file."""
        if not _CONFIG_PATH.exists():
            return
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            self.hotkeys = data.get("hotkeys", [])
        except Exception as e:
            print(f"[Hotkeys] Load error: {e}")
            self.hotkeys = []

    def start(self):
        """Start listening for hotkeys in a background thread."""
        if not _HAS_KEYBOARD:
            print("[Hotkeys] Info: 'keyboard' module not installed. Install with 'pip install keyboard' to enable global background hotkeys.")
            return

        self.load_hotkeys()
        if not self.hotkeys:
            return

        self._running = True
        self._listener_thread = threading.Thread(target=self._loop, daemon=True)
        self._listener_thread.start()
        print("[Hotkeys] Global keyboard hotkeys engine active.")

    def _loop(self):
        """Bind keys and block."""
        try:
            # Register each hotkey
            for hk in self.hotkeys:
                keys = hk.get("keys", "")
                action = hk.get("action", "")
                if keys and action:
                    keyboard.add_hotkey(keys, self._trigger_action, args=(action, keys))
                    print(f"  [+] Registered hotkey: {keys} -> {action}")

            # Keep thread alive
            while self._running:
                time.sleep(0.5)
        except Exception as e:
            print(f"[Hotkeys] Thread error: {e}")
            traceback.print_exc()

    def stop(self):
        """Unregister all hotkeys."""
        self._running = False
        if _HAS_KEYBOARD:
            try:
                keyboard.clear_all_hotkeys()
            except Exception:
                pass

    def _trigger_action(self, action_name: str, keys: str):
        """Execute the hotkey action."""
        print(f"[Hotkeys] Hotkey triggered: {keys} -> {action_name}")
        if not self.assistant:
            return

        try:
            if action_name == "toggle_listen":
                # Toggle muted state in the assistant UI or toggle active listening
                ui = self.assistant.ui
                if hasattr(ui, "toggle_mute"):
                    ui.toggle_mute()
                else:
                    ui.muted = not getattr(ui, "muted", False)
                    state = "MUTED" if ui.muted else "LISTENING"
                    ui.set_state(state)
                    ui.write_log(f"SYS: Voice assistant {state.lower()} via hotkey.")

            elif action_name == "ask_clipboard":
                from actions.clipboard_utils import get_clipboard_text
                clip = get_clipboard_text().strip()
                if clip:
                    self.assistant.ui.write_log(f"Hotkey: Clipboard Query triggered.")
                    # Process in helper thread
                    threading.Thread(
                        target=lambda: self.assistant._on_text_command(f"Explain or process this clipboard content:\n\n{clip}"),
                        daemon=True
                    ).start()

            elif action_name == "screenshot_analyze":
                self.assistant.ui.write_log(f"Hotkey: Screenshot Analysis triggered.")
                # Run the screenshot fix or analysis skill/goal
                threading.Thread(
                    target=lambda: self.assistant._on_text_command("take screenshot and analyze the screen for any visible errors"),
                    daemon=True
                ).start()

        except Exception as e:
            print(f"[Hotkeys] Failed to execute hotkey action '{action_name}': {e}")
