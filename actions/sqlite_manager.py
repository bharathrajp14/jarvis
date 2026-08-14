# actions/sqlite_manager.py — SQLite Database Maintenance & Query Action for JARVIS MK37
"""
Autonomous action for SQLite database schema inspection, vacuum optimization, table stats,
and backup creation.
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path


class SQLiteManagerAction:
    """SQLite Database Maintenance and Administration Action."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()

    def inspect_db(self) -> str:
        if not self.db_path.exists():
            return f"Error: Database file '{self.db_path}' does not exist."

        try:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cur.fetchall()]
            
            stats = []
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t};")
                count = cur.fetchone()[0]
                stats.append(f"  ● Table '{t}': {count} rows")
            conn.close()

            size_mb = self.db_path.stat().st_size / (1024 * 1024)
            return (
                f"🗄️ SQLite DB Summary ('{self.db_path.name}'):\n"
                f"- File Size: {size_mb:.2f} MB\n"
                f"- Tables ({len(tables)}):\n" + "\n".join(stats)
            )
        except Exception as e:
            return f"Database inspection failed: {e}"

    def optimize_db(self) -> str:
        if not self.db_path.exists():
            return f"Error: Database file '{self.db_path}' does not exist."

        try:
            orig_size = self.db_path.stat().st_size
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("VACUUM;")
            conn.execute("PRAGMA optimize;")
            conn.close()
            new_size = self.db_path.stat().st_size
            saved_kb = (orig_size - new_size) / 1024
            return f"✅ Database VACUUM complete. Reclaimed {saved_kb:.1f} KB."
        except Exception as e:
            return f"Database optimization failed: {e}"

    def backup_db(self, backup_dir: str | Path = ".") -> str:
        if not self.db_path.exists():
            return f"Error: Database file '{self.db_path}' does not exist."

        b_dir = Path(backup_dir).resolve()
        b_dir.mkdir(parents=True, exist_ok=True)
        target = b_dir / f"{self.db_path.stem}_backup{self.db_path.suffix}"
        
        try:
            shutil.copy2(self.db_path, target)
            return f"✅ Database Backup Created: '{target}' ({target.stat().st_size / 1024:.1f} KB)"
        except Exception as e:
            return f"Backup failed: {e}"
