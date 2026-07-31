# watchers/file_watcher.py — Event-Driven Workspace File Watcher
"""
FileWatcher monitors workspace file modifications and publishes file.changed events to EventBus.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional
from events.bus import get_event_bus

logger = logging.getLogger("JARVIS.FileWatcher")


class FileWatcher:
    """
    Passive filesystem modification watcher emitting event notifications into EventBus.
    """

    def __init__(self, watch_path: Optional[str] = None):
        self.watch_path = Path(watch_path or os.getcwd())
        self.event_bus = get_event_bus()
        self._file_mtimes: Dict[str, float] = {}

    def scan_for_changes(self) -> int:
        """
        Scan watched path for modified files and publish change events.
        """
        changes_detected = 0
        try:
            ignored_parts = {"__pycache__", ".git", ".venv", "venv", "node_modules", "build", "dist", ".pytest_cache"}
            current_paths = set()
            for file_path in self.watch_path.rglob("*.py"):
                if file_path.is_file() and not any(part in file_path.parts for part in ignored_parts):
                    str_path = str(file_path)
                    current_paths.add(str_path)
                    mtime = file_path.stat().st_mtime
                    
                    if str_path in self._file_mtimes:
                        if mtime > self._file_mtimes[str_path]:
                            changes_detected += 1
                            logger.info(f"📂 FileWatcher: Change detected in {file_path.name}")
                            self.event_bus.publish(
                                "file.changed",
                                {"file_path": str_path, "filename": file_path.name, "mtime": mtime},
                            )
                    self._file_mtimes[str_path] = mtime

            # Cleanup deleted files to prevent memory leak
            for obs in list(set(self._file_mtimes.keys()) - current_paths):
                del self._file_mtimes[obs]
        except Exception as e:
            logger.warning(f"FileWatcher scan error: {e}")

        return changes_detected
