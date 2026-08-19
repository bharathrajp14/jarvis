# actions/app_tracker.py — Application Launch Tracker & Persistent Event Store
"""
Application Launch Tracker & Persistent SQLite Storage for BR-Jarvis.
Records application start events, tracks application usage metrics,
and provides analytics on app starts.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("JARVIS.AppTracker")


def _get_db_path() -> Path:
    db_dir = Path.cwd() / ".jarvis"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "app_tracker.db"


class AppStartTracker:
    """
    Persistent tracker engine for application launch events and usage telemetry.
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
        """Create database tables if they do not exist."""
        try:
            with self._db_session() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_launches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_name TEXT NOT NULL,
                        exe_path TEXT,
                        pid INTEGER,
                        launch_time TEXT DEFAULT (datetime('now', 'localtime')),
                        timestamp REAL,
                        source TEXT DEFAULT 'system_watcher',
                        details TEXT
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_app_launches_name ON app_launches(app_name);
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_app_launches_time ON app_launches(timestamp);
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize app tracker database: {e}")

    def log_launch(
        self,
        app_name: str,
        exe_path: str = "",
        pid: int = 0,
        source: str = "system_watcher",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record an application launch event into the SQLite database store.
        """
        if not app_name:
            return False

        try:
            dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ts = time.time()
            details_json = json.dumps(details or {})

            with self._db_session() as conn:
                conn.execute(
                    """
                    INSERT INTO app_launches (app_name, exe_path, pid, launch_time, timestamp, source, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (app_name, exe_path, pid, dt_str, ts, source, details_json),
                )
                conn.commit()
            logger.info(f"🚀 App Start Logged: '{app_name}' (PID {pid}) via [{source}]")
            return True
        except Exception as e:
            logger.error(f"Error logging app launch for '{app_name}': {e}")
            return False

    def get_history(self, limit: int = 50, app_name: str = "") -> List[Dict[str, Any]]:
        """
        Retrieve launch history records.
        """
        results = []
        try:
            with self._db_session() as conn:
                cursor = conn.cursor()
                if app_name:
                    cursor.execute(
                        """
                        SELECT id, app_name, exe_path, pid, launch_time, timestamp, source, details
                        FROM app_launches
                        WHERE LOWER(app_name) LIKE ?
                        ORDER BY id DESC LIMIT ?
                        """,
                        (f"%{app_name.lower()}%", limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, app_name, exe_path, pid, launch_time, timestamp, source, details
                        FROM app_launches
                        ORDER BY id DESC LIMIT ?
                        """,
                        (limit,),
                    )
                rows = cursor.fetchall()

                for r in rows:
                    details_dict = {}
                    if r["details"]:
                        try:
                            details_dict = json.loads(r["details"])
                        except Exception:
                            pass
                    results.append(
                        {
                            "id": r["id"],
                            "app_name": r["app_name"],
                            "exe_path": r["exe_path"],
                            "pid": r["pid"],
                            "launch_time": r["launch_time"],
                            "source": r["source"],
                            "details": details_dict,
                        }
                    )
        except Exception as e:
            logger.error(f"Error fetching app launch history: {e}")
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Compute usage statistics and launch frequency for applications.
        """
        stats: Dict[str, Any] = {"total_launches": 0, "unique_apps": 0, "most_launched": [], "recent_launches": []}
        try:
            with self._db_session() as conn:
                cursor = conn.cursor()

                # Total count
                cursor.execute("SELECT COUNT(*) FROM app_launches")
                stats["total_launches"] = cursor.fetchone()[0]

                # Most launched apps
                cursor.execute(
                    """
                    SELECT app_name, COUNT(*) as cnt, MAX(launch_time) as last_launched
                    FROM app_launches
                    GROUP BY LOWER(app_name)
                    ORDER BY cnt DESC LIMIT 10
                    """
                )
                top_rows = cursor.fetchall()
                stats["unique_apps"] = len(top_rows)
                stats["most_launched"] = [
                    {"app_name": r["app_name"], "count": r["cnt"], "last_launched": r["last_launched"]}
                    for r in top_rows
                ]

                # Recent 5 launches
                cursor.execute(
                    """
                    SELECT app_name, launch_time, source
                    FROM app_launches
                    ORDER BY id DESC LIMIT 5
                    """
                )
                stats["recent_launches"] = [
                    {"app_name": r["app_name"], "launch_time": r["launch_time"], "source": r["source"]}
                    for r in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error computing app statistics: {e}")
        return stats


# Global singleton instance
_tracker_instance = AppStartTracker()


def get_app_tracker() -> AppStartTracker:
    return _tracker_instance


def log_app_launch(
    app_name: str,
    exe_path: str = "",
    pid: int = 0,
    source: str = "system_watcher",
    details: Optional[Dict[str, Any]] = None,
) -> bool:
    return get_app_tracker().log_launch(app_name, exe_path=exe_path, pid=pid, source=source, details=details)
