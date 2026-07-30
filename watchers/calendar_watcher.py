# watchers/calendar_watcher.py — Background Calendar Event & Reminder Watcher
"""
CalendarWatcher continuously polls for upcoming calendar events,
triggering native OS toast notifications and alert events when reminders are due.
"""
from __future__ import annotations

import sys
import time
import logging
import threading
import subprocess
from events.bus import get_event_bus
from actions.calendar_engine import get_calendar_engine

logger = logging.getLogger("JARVIS.CalendarWatcher")


class CalendarWatcher:
    """
    Background thread watcher monitoring upcoming calendar events.
    """

    def __init__(self):
        self.event_bus = get_event_bus()
        self.calendar = get_calendar_engine()
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()

    def _poll_loop(self):
        """Poll every 15 seconds for due event reminders."""
        while self._running:
            try:
                now_ts = time.time()
                events = self.calendar.list_events(days=1)

                with self.calendar._db_session() as conn:
                    cursor = conn.cursor()
                    for ev in events:
                        ev_id = ev["id"]
                        title = ev["title"]
                        start_time = ev["start_time"]
                        rem_mins = ev.get("reminder_minutes", 15)

                        # Fetch raw event details to check start timestamp & notified flag
                        cursor.execute("SELECT start_timestamp, notified FROM calendar_events WHERE id = ?", (ev_id,))
                        row = cursor.fetchone()
                        if not row or row["notified"]:
                            continue

                        start_ts = row["start_timestamp"]
                        trigger_ts = start_ts - (rem_mins * 60)

                        if now_ts >= trigger_ts:
                            logger.info(f"⏰ Calendar Reminder Alert: '{title}' starting at {start_time}")
                            self._trigger_toast(title, start_time, ev.get("location", ""))

                            # Mark notified
                            cursor.execute("UPDATE calendar_events SET notified = 1 WHERE id = ?", (ev_id,))
                            conn.commit()

                            self.event_bus.publish("calendar.reminder", {
                                "id": ev_id,
                                "title": title,
                                "start_time": start_time
                            })
            except Exception as e:
                logger.debug(f"CalendarWatcher polling error: {e}")

            time.sleep(15)

    def _trigger_toast(self, title: str, start_time: str, location: str):
        """Display native OS toast alert."""
        loc_str = f" @ {location}" if location else ""
        text = f"'{title}' starting at {start_time}{loc_str}"
        print(f"[Calendar Alert] ⏰ EVENT REMINDER: {text}")

        if sys.platform == "win32":
            try:
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
                $template = @"
                <toast>
                    <visual>
                        <binding template="ToastGeneric">
                            <text>📅 Calendar Reminder</text>
                            <text>{text}</text>
                        </binding>
                    </visual>
                    <audio src="ms-winsoundevent:Notification.Default"/>
                </toast>
"@
                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("BR JARVIS Calendar").Show($toast)
                '''
                subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.debug(f"Toast notification error: {e}")


# Global singleton watcher instance
_calendar_watcher = CalendarWatcher()
_calendar_watcher.start()


def get_calendar_watcher() -> CalendarWatcher:
    return _calendar_watcher
