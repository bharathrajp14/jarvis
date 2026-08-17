# actions/calendar_engine.py — Mobile Gemini-Style Calendar & Task Engine for BR-Jarvis
"""
Mobile Gemini-Style Calendar & Task Engine for BR-Jarvis.
Manages tasks and calendar events with natural language datetime parsing,
SQLite persistence, iCalendar (.ics) exports, and contact attendee invitations.
"""
from __future__ import annotations

import re
import json
import sqlite3
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Generator

logger = logging.getLogger("JARVIS.CalendarEngine")


def _get_db_path() -> Path:
    db_dir = Path.cwd() / ".jarvis"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "calendar.db"


class CalendarEngine:
    """
    Calendar and Task Engine for managing events, reminders, and schedules.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _get_db_path()
        self._init_db()

    @contextmanager
    def _db_session(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a SQLite connection and ensuring proper closure."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)

        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize calendar database table."""
        try:
            with self._db_session() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS calendar_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        start_time TEXT NOT NULL,
                        start_timestamp REAL NOT NULL,
                        end_time TEXT,
                        end_timestamp REAL,
                        location TEXT,
                        attendees TEXT,
                        status TEXT DEFAULT 'confirmed',
                        reminder_minutes INTEGER DEFAULT 15,
                        notified INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT (datetime('now', 'localtime'))
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cal_start ON calendar_events(start_timestamp);
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize calendar DB: {e}")

    def parse_datetime(self, time_str: str) -> tuple[str, float]:
        """
        Parse natural language date/time strings into (ISO string, unix timestamp).
        Supports: 'tomorrow 3pm', 'today 5pm', 'in 2 hours', '2026-08-01 10:00'.
        """
        now = datetime.now()
        low = time_str.lower().strip()

        # 1. Check relative duration e.g. "in 2 hours", "in 30 mins"
        m_rel = re.search(r"in\s+(\d+)\s*(hour|hr|minute|min|sec)", low)
        if m_rel:
            num = int(m_rel.group(1))
            unit = m_rel.group(2)
            if "hour" in unit or "hr" in unit:
                dt = now + timedelta(hours=num)
            elif "min" in unit:
                dt = now + timedelta(minutes=num)
            else:
                dt = now + timedelta(seconds=num)
            return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.timestamp()

        # 2. Check "tomorrow" or "today" keywords
        base_date = now.date()
        if "tomorrow" in low:
            base_date = now.date() + timedelta(days=1)
            low = low.replace("tomorrow", "").strip()
        elif "today" in low:
            base_date = now.date()
            low = low.replace("today", "").strip()

        # Check time format e.g. "3pm", "3:30 pm", "14:00"
        time_part = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
        if time_part:
            hour = int(time_part.group(1))
            minute = int(time_part.group(2)) if time_part.group(2) else 0
            ampm = time_part.group(3)

            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

            dt = datetime.combine(base_date, datetime.min.time()).replace(hour=hour, minute=minute)
            if dt < now and "tomorrow" not in time_str.lower() and "today" not in time_str.lower():
                dt += timedelta(days=1)
            return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.timestamp()

        # 3. Standard strptime format parsing fallbacks
        for fmt in (
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
            "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M"
        ):
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.timestamp()
            except ValueError:
                pass

        # Default fallback: 1 hour from now
        dt = now + timedelta(hours=1)
        return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.timestamp()

    def create_event(
        self,
        title: str,
        start_time_str: str,
        end_time_str: Optional[str] = None,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
        reminder_minutes: int = 15,
        notify_whatsapp: bool = False
    ) -> Dict[str, Any]:
        """
        Create a calendar event or task.
        """
        if not title:
            return {"success": False, "error": "Event title is required."}

        formatted_start, start_ts = self.parse_datetime(start_time_str)

        if end_time_str:
            formatted_end, end_ts = self.parse_datetime(end_time_str)
        else:
            # Default duration: 1 hour
            end_dt = datetime.fromtimestamp(start_ts) + timedelta(hours=1)
            formatted_end, end_ts = end_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.timestamp()

        attendees_list = attendees or []
        attendees_json = json.dumps(attendees_list)

        try:
            with self._db_session() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO calendar_events (title, description, start_time, start_timestamp, end_time, end_timestamp, location, attendees, reminder_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (title, description, formatted_start, start_ts, formatted_end, end_ts, location, attendees_json, reminder_minutes)
                )
                conn.commit()
                event_id = cursor.lastrowid

            # Optional WhatsApp notification to attendees
            if notify_whatsapp and attendees_list:
                try:
                    from brjarvis.actions.whatsapp_automation import get_whatsapp_automation
                    wa = get_whatsapp_automation()
                    msg = f"📅 Calendar Event Invite: '{title}' on {formatted_start}. Location: {location or 'N/A'}"
                    for att in attendees_list:
                        wa.send_message(recipient=att, message_text=msg)
                except Exception as e:
                    logger.error(f"Failed WhatsApp notification to attendees: {e}")

            return {
                "success": True,
                "event_id": event_id,
                "title": title,
                "start_time": formatted_start,
                "end_time": formatted_end,
                "location": location,
                "attendees": attendees_list
            }
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {"success": False, "error": str(e)}

    def list_events(self, days_ahead: int = 7, days: int = 7, include_past: bool = False, **kwargs) -> List[Dict[str, Any]]:
        """List upcoming events within specified number of days."""
        num_days = days_ahead if days_ahead != 7 else days
        results = []
        now_ts = time.time()
        future_ts = now_ts + (num_days * 86400)
        min_ts = 0.0 if include_past else (now_ts - 3600)

        try:
            with self._db_session() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, description, start_time, end_time, location, attendees, reminder_minutes, status
                    FROM calendar_events
                    WHERE start_timestamp >= ? AND start_timestamp <= ?
                    ORDER BY start_timestamp ASC
                    """,
                    (min_ts, future_ts)
                )
                rows = cursor.fetchall()
                for r in rows:
                    att_list = []
                    if r["attendees"]:
                        try:
                            att_list = json.loads(r["attendees"])
                        except Exception:
                            pass
                    results.append({
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"],
                        "start_time": r["start_time"],
                        "end_time": r["end_time"],
                        "location": r["location"],
                        "attendees": att_list,
                        "reminder_minutes": r["reminder_minutes"],
                        "status": r["status"]
                    })
        except Exception as e:
            logger.error(f"Error listing calendar events: {e}")
        return results

    def search_events(self, query: str) -> List[Dict[str, Any]]:
        """Search calendar events by keyword query."""
        results = []
        q = f"%{query.strip().lower()}%"
        try:
            with self._db_session() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, description, start_time, end_time, location, attendees
                    FROM calendar_events
                    WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(location) LIKE ?
                    ORDER BY start_timestamp DESC
                    """,
                    (q, q, q)
                )
                rows = cursor.fetchall()
                for r in rows:
                    results.append({
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"],
                        "start_time": r["start_time"],
                        "end_time": r["end_time"],
                        "location": r["location"]
                    })
        except Exception as e:
            logger.error(f"Error searching calendar events: {e}")
        return results

    def delete_event(self, event_id: int) -> bool:
        """Delete a calendar event by ID."""
        try:
            with self._db_session() as conn:
                conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            return False


# Global singleton instance
_calendar_instance = CalendarEngine()


def get_calendar_engine() -> CalendarEngine:
    return _calendar_instance
