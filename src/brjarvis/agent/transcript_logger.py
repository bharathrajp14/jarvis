# agent/transcript_logger.py — Antigravity-Style JSONL Trajectory Logger
"""
Transcript Trajectory Logger for BR JARVIS.
Logs chronological step execution, tool calls, model thoughts, and sub-agent outputs
into JSON Lines format (transcript.jsonl & transcript_full.jsonl).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_log_dir() -> Path:
    from brjarvis.core.paths import paths

    ldir = paths.LOG_ROOT / "transcripts"
    ldir.mkdir(parents=True, exist_ok=True)
    return ldir


class TranscriptLogger:
    """Logs agent execution trajectory steps into transcript.jsonl & transcript_full.jsonl."""

    _instance: Optional[TranscriptLogger] = None

    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.dir = _get_log_dir()
        self.compact_file = self.dir / "transcript.jsonl"
        self.full_file = self.dir / "transcript_full.jsonl"
        self.step_index = 0

    @classmethod
    def get_instance(cls, session_id: str = "default_session") -> TranscriptLogger:
        if cls._instance is None:
            cls._instance = TranscriptLogger(session_id=session_id)
        return cls._instance

    def log_step(
        self,
        source: str,
        step_type: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        status: str = "DONE",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a single trajectory step into JSONL files."""
        self.step_index += 1
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        full_entry = {
            "step_index": self.step_index,
            "session_id": self.session_id,
            "timestamp": timestamp,
            "source": source,
            "type": step_type,
            "status": status,
            "content": content,
            "tool_calls": tool_calls or [],
            "metadata": metadata or {},
            "is_truncated": False,
        }

        # Compact entry truncates content > 500 chars
        compact_entry = dict(full_entry)
        if len(content) > 500:
            compact_entry["content"] = content[:500] + "... [truncated]"
            compact_entry["is_truncated"] = True

        try:
            with open(self.full_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(full_entry, ensure_ascii=False) + "\n")
            with open(self.compact_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(compact_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def get_transcript_logger(session_id: str = "default_session") -> TranscriptLogger:
    return TranscriptLogger.get_instance(session_id=session_id)
