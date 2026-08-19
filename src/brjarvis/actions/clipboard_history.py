# actions/clipboard_history.py — Clipboard History Tracker
"""
Background clipboard history monitor for JARVIS MK37.
Logs clipboard copies to a SQLite database and provides search tools.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time

from brjarvis.memory.persistent_store import get_memory_dir
from brjarvis.tools.registry import register_tool

from .clipboard_utils import get_clipboard_text

logger = logging.getLogger(__name__)


class ClipboardTracker:
    """Monitors OS clipboard in a background thread and stores entries in SQLite."""

    def __init__(self):
        db_dir = get_memory_dir("user")
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "clipboard_history.db"
        self._init_db()
        self._running = False
        self._thread = None

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clipboard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    content TEXT UNIQUE,
                    char_count INTEGER
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def start(self):
        """Start tracking clipboard in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        last_val = ""
        while self._running:
            try:
                val = get_clipboard_text()
                if val and val.strip() and val != last_val:
                    last_val = val
                    self._save_entry(val)
            except Exception as e:
                logger.debug("Suppressed exception: %s", e)
            time.sleep(1.0)

    def _save_entry(self, content: str):
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO clipboard (timestamp, content, char_count) VALUES (datetime('now', 'localtime'), ?, ?)",
                (content, len(content)),
            )
            conn.commit()
        except Exception as e:
            logger.debug("Suppressed exception: %s", e)
        finally:
            conn.close()

    def search(self, query: str, limit: int = 15) -> list[dict]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, content FROM clipboard WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit),
            )
            return [{"timestamp": r["timestamp"], "content": r["content"]} for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_recent(self, limit: int = 15) -> list[dict]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, content FROM clipboard ORDER BY id DESC LIMIT ?", (limit,))
            return [{"timestamp": r["timestamp"], "content": r["content"]} for r in cursor.fetchall()]
        finally:
            conn.close()


# Singleton
_tracker = ClipboardTracker()
_tracker.start()


@register_tool(
    name="clipboard_history",
    description="Retrieve, list, or search clipboard history logged by the background tracker.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "list, search"},
            "query": {"type": "string", "description": "Keyword to search for (required for action='search')"},
            "limit": {"type": "integer", "description": "Max entries to return (default 10)"},
        },
        "required": ["action"],
    },
)
def tool_clipboard_history(args: dict) -> str:
    action = args.get("action", "list").lower()
    query = args.get("query", "")
    limit = args.get("limit", 10)

    if action == "search":
        if not query:
            return "ERROR: Query parameter is required for clipboard search."
        results = _tracker.search(query, limit)
        if not results:
            return f"No clipboard history found matching '{query}'."
        lines = [f"Clipboard search results for '{query}':"]
        for i, r in enumerate(results, 1):
            short = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
            lines.append(f"  {i}. [{r['timestamp']}] {short!r}")
        return "\n".join(lines)
    else:
        results = _tracker.get_recent(limit)
        if not results:
            return "No clipboard history recorded yet."
        lines = ["Recent clipboard history:"]
        for i, r in enumerate(results, 1):
            short = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
            lines.append(f"  {i}. [{r['timestamp']}] {short!r}")
        return "\n".join(lines)
