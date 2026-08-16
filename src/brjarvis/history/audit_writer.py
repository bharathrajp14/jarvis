# history/audit_writer.py — Structured & Rotated JSON Audit Writer for JARVIS MK37
"""
Structured JSON audit writer for JARVIS MK37.

Writes to:
  ~/.jarvis/history/audit.jsonl  — structured JSON Lines (machine-readable)
  ~/.jarvis/audit.log            — human-readable plain text (grep-friendly)

Features:
  - Thread-safe writes via threading.Lock()
  - Safe JSON argument truncation without decode syntax errors
  - Automatic log rotation (10 MB cap per log file, max 3 backups)
"""
from __future__ import annotations

import logging
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_JSONL_PATH = Path.home() / ".jarvis" / "history" / "audit.jsonl"
_PLAINTEXT_PATH = Path.home() / ".jarvis" / "audit.log"
_MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB per file
_MAX_BACKUPS = 3
_lock = threading.Lock()

# Module-level session_id — set by the orchestrator on session start
_current_session_id: str = ""


def set_session_id(session_id: str) -> None:
    """Set the current session ID for audit entries."""
    global _current_session_id
    _current_session_id = session_id


def _rotate_if_needed(file_path: Path) -> None:
    """Rotate log file if size exceeds _MAX_LOG_BYTES."""
    try:
        if not file_path.exists() or file_path.stat().st_size < _MAX_LOG_BYTES:
            return
        
        for i in range(_MAX_BACKUPS - 1, 0, -1):
            s_file = file_path.with_name(f"{file_path.name}.{i}")
            d_file = file_path.with_name(f"{file_path.name}.{i + 1}")
            if s_file.exists():
                if d_file.exists():
                    d_file.unlink()
                s_file.rename(d_file)
        
        target = file_path.with_name(f"{file_path.name}.1")
        if target.exists():
            target.unlink()
        file_path.rename(target)
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
def _truncate_args(args: Any, max_len: int = 500) -> Any:
    """Safely truncate arguments for audit storage without JSON syntax errors."""
    if args is None:
        return None
    if isinstance(args, (int, float, bool)):
        return args
    if isinstance(args, dict):
        truncated = {}
        for k, v in list(args.items())[:15]:
            truncated[str(k)] = _truncate_args(v, max_len=100)
        return truncated
    if isinstance(args, list):
        return [_truncate_args(item, max_len=50) for item in args[:10]]
    
    s = str(args)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def write_audit(
    tool: str,
    args: dict | str | None,
    decision: str,
    latency_ms: int = 0,
    error: str | None = None,
    session_id: str | None = None,
) -> None:
    """Write a structured audit entry to both JSONL and plain-text logs.

    Args:
        tool:       name of the tool that was invoked
        args:       tool arguments (dict or string, safely truncated)
        decision:   authorization decision (ALLOWED, DENIED, CONFIRMED, etc.)
        latency_ms: execution time in milliseconds
        error:      error message if the tool call failed, or None
        session_id: override session ID (uses module-level default if None)
    """
    sid = session_id or _current_session_id
    now = datetime.now(tz=timezone.utc)

    args_truncated = _truncate_args(args)

    # Build the JSONL entry
    entry = {
        "ts": now.isoformat(),
        "session_id": sid,
        "tool": tool,
        "args": args_truncated,
        "decision": decision,
        "latency_ms": latency_ms,
        "error": error,
    }

    # Build the human-readable line
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    args_summary = ""
    if args_truncated:
        try:
            args_summary = json.dumps(args_truncated, default=str)[:200]
        except Exception:
            args_summary = str(args_truncated)[:200]

    plain_line = f"[{timestamp_str}] {decision:20s} | {tool:25s} | {args_summary}"
    if error:
        plain_line += f" | ERROR: {error[:100]}"
    if latency_ms:
        plain_line += f" | {latency_ms}ms"
    plain_line += "\n"

    with _lock:
        try:
            _rotate_if_needed(_JSONL_PATH)
            _JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_JSONL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")
        except Exception:
            pass  # Audit logging must never crash the system

        try:
            _rotate_if_needed(_PLAINTEXT_PATH)
            _PLAINTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_PLAINTEXT_PATH, "a", encoding="utf-8") as f:
                f.write(plain_line)
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
