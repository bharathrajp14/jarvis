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
            for file_path in self.watch_path.glob("*.py"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    str_path = str(file_path)
                    
                    if str_path in self._file_mtimes:
                        if mtime > self._file_mtimes[str_path]:
                            changes_detected += 1
                            logger.info(f"📂 FileWatcher: Change detected in {file_path.name}")
                            self.event_bus.publish(
                                "file.changed",
                                {"file_path": str_path, "filename": file_path.name, "mtime": mtime},
                            )
                    self._file_mtimes[str_path] = mtime
        except Exception as e:
            logger.warning(f"FileWatcher scan error: {e}")

        return changes_detected
