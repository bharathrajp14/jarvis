# actions/reminders.py — Smart Reminders & System Toast Notifications for BR-JARVIS
"""
Pika Voice-style Smart Reminder Engine.
Schedules one-time or recurring reminders, tracks active tasks,
and triggers native Windows desktop notification toasts with sound alerts.
"""
from __future__ import annotations

import os
import sys
import time
import json
import re
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

_REMINDERS_FILE = Path(__file__).resolve().parent.parent / "workspace" / "reminders.json"


class ReminderManager:
    """Thread-safe background reminder scheduler."""

    def __init__(self):
        self._reminders: list[dict] = []
        self._lock = threading.Lock()
        self._running = False
        self._load()
        self.start()

    def _load(self):
        """Load reminders from persistent storage."""
        with self._lock:
            if _REMINDERS_FILE.exists():
                try:
                    data = json.loads(_REMINDERS_FILE.read_text(encoding="utf-8"))
                    self._reminders = data.get("reminders", [])
                except Exception:
                    self._reminders = []

    def _save(self):
        """Save reminders to persistent storage."""
        try:
            _REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            _REMINDERS_FILE.write_text(
                json.dumps({"reminders": self._reminders}, indent=2), encoding="utf-8"
            )
        except Exception as e:
            print(f"[Reminders] Save error: {e}")

    def start(self):
        """Start background reminder polling thread."""
        if self._running:
            return
        self._running = True
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()

    def _poll_loop(self):
        """Poll every 5 seconds for due reminders."""
        while self._running:
            now = time.time()
            due = []
            with self._lock:
                for r in self._reminders:
                    if not r.get("completed", False) and r.get("trigger_at", 0) <= now:
                        r["completed"] = True
                        due.append(r)
                if due:
                    self._save()

            for r in due:
                self._trigger_toast(r["text"])

            time.sleep(5)

    def _trigger_toast(self, text: str):
        """Trigger native OS desktop notification toast."""
        print(f"[Reminder Alert] ⏰ REMINDER: {text}")

        if sys.platform == "win32":
            try:
                # Windows PowerShell Toast Notification
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
                $template = @"
                <toast>
                    <visual>
                        <binding template="ToastGeneric">
                            <text>⏰ BR JARVIS Reminder</text>
                            <text>{text}</text>
                        </binding>
                    </visual>
                    <audio src="ms-winsoundevent:Notification.Default"/>
                </toast>
"@
                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("BR JARVIS").Show($toast)
                '''
                subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], shell=False)
            except Exception:
                pass

    def add_reminder(self, text: str, delay_seconds: int = 0, target_time_str: str = "") -> dict:
        """Add a new reminder."""
        now = time.time()
        trigger_at = now + delay_seconds

        if target_time_str:
            try:
                # Parse times like "9:00 AM", "14:30", "tomorrow 9am"
                low = target_time_str.lower().strip()
                m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
                if m:
                    hr = int(m.group(1))
                    mn = int(m.group(2) or 0)
                    ampm = (m.group(3) or "").lower()
                    if ampm == "pm" and hr < 12:
                        hr += 12
                    elif ampm == "am" and hr == 12:
                        hr = 0

                    dt_target = datetime.now().replace(hour=hr, minute=mn, second=0, microsecond=0)
                    if dt_target.timestamp() <= now:
                        dt_target += timedelta(days=1)
                    trigger_at = dt_target.timestamp()
            except Exception:
                pass

        rem = {
            "id": f"rem_{int(now)}_{len(self._reminders)}",
            "text": text,
            "created_at": now,
            "trigger_at": trigger_at,
            "trigger_formatted": datetime.fromtimestamp(trigger_at).strftime("%I:%M %p on %b %d"),
            "completed": False,
        }

        with self._lock:
            self._reminders.append(rem)
            self._save()

        return rem

    def list_reminders(self) -> list[dict]:
        """List active pending reminders."""
        with self._lock:
            return [r for r in self._reminders if not r.get("completed", False)]


_global_reminder_mgr: ReminderManager | None = None


def get_reminder_manager() -> ReminderManager:
    global _global_reminder_mgr
    if _global_reminder_mgr is None:
        _global_reminder_mgr = ReminderManager()
    return _global_reminder_mgr


def reminder_tool_action(action: str = "add", text: str = "", delay_seconds: int = 0, time_str: str = "") -> str:
    """Tool function for adding or listing reminders."""
    mgr = get_reminder_manager()
    act = (action or "add").lower().strip()

    if act in ("add", "create", "set"):
        if not text:
            return "ERROR: Reminder text is required."
        rem = mgr.add_reminder(text, delay_seconds=delay_seconds, target_time_str=time_str)
        return f"⏰ Reminder set: '{rem['text']}' for {rem['trigger_formatted']}."
    elif act in ("list", "show", "view"):
        pending = mgr.list_reminders()
        if not pending:
            return "No active reminders pending."
        lines = [f"- [{r['id']}] {r['text']} (Due: {r['trigger_formatted']})" for r in pending]
        return "⏰ Active Pending Reminders:\n" + "\n".join(lines)
    else:
        return f"ERROR: Unknown action '{action}'"
