# memory/archiver.py — Memory Consolidation, Aging & Disk Archiver for JARVIS MK37
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("JARVIS.MemoryArchiver")

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
ARCHIVE_FILE = WORKSPACE_DIR / "logs" / "memory_archive.jsonl"
ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)


class MemoryArchiver:
    """Manages memory aging, consolidation, and disk archiving."""

    def __init__(self, max_age_days: int = 30):
        self.max_age_seconds = max_age_days * 86400

    def archive_entry(self, memory_type: str, data: Dict[str, Any]) -> None:
        """Write a stale memory item to permanent JSONL archive."""
        record = {
            "archived_at": time.time(),
            "memory_type": memory_type,
            "data": data,
        }
        try:
            with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            logger.debug(f"Archived {memory_type} memory item to {ARCHIVE_FILE.name}")
        except Exception as e:
            logger.error(f"Failed to archive memory entry: {e}")

    def consolidate_history(self, history_list: List[Dict[str, Any]], max_keep: int = 50) -> List[Dict[str, Any]]:
        """Consolidate chat history by archiving items beyond max_keep limit."""
        if len(history_list) <= max_keep:
            return history_list

        overflow_count = len(history_list) - max_keep
        to_archive = history_list[:overflow_count]
        retained = history_list[overflow_count:]

        for item in to_archive:
            self.archive_entry("episodic_conversation", item)

        logger.info(f"Consolidated memory: Archived {len(to_archive)} history turns, retained {len(retained)}")
        return retained
