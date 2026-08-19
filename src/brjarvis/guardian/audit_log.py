# guardian/audit_log.py — Append-Only Human-Readable Autonomy Audit Log
"""
Append-only Audit Log for autonomous actions, self-upgrades, and routing shifts.
Includes automatic log file rotation.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = Path("workspace/logs/autonomy_audit.jsonl")
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per audit log
_MAX_ROTATIONS = 3  # keep up to 3 rotated log files


class AuditLog:
    """Human-readable append-only ledger of autonomous events."""

    @classmethod
    def _rotate_if_needed(cls) -> None:
        """Rotate audit file if size exceeds _MAX_BYTES. Keeps up to _MAX_ROTATIONS backups."""
        try:
            if not AUDIT_LOG_FILE.exists() or AUDIT_LOG_FILE.stat().st_size < _MAX_BYTES:
                return
            # Shift existing rotations: .2 → .3, .1 → .2, current → .1
            for i in range(_MAX_ROTATIONS, 1, -1):
                src = AUDIT_LOG_FILE.with_name(f"autonomy_audit.jsonl.{i - 1}")
                dst = AUDIT_LOG_FILE.with_name(f"autonomy_audit.jsonl.{i}")
                if src.exists():
                    if dst.exists():
                        dst.unlink()
                    src.rename(dst)
            target = AUDIT_LOG_FILE.with_name("autonomy_audit.jsonl.1")
            if target.exists():
                target.unlink()
            AUDIT_LOG_FILE.rename(target)
        except Exception as e:
            logger.exception("Boot critical exception encountered in guardian/audit_log.py")
            raise e

    @classmethod
    def log(
        cls,
        event_type: str,
        title: str,
        details: dict | str,
        risk_level: str = "LOW",
        applied: bool = True,
    ) -> dict:
        """Log an autonomous action or patch to the audit log."""
        record = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "title": title,
            "details": details if isinstance(details, dict) else {"message": str(details)},
            "risk_level": risk_level.upper(),
            "applied": applied,
        }
        try:
            cls._rotate_if_needed()
            AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.exception("Boot critical exception encountered in guardian/audit_log.py")
            raise e
        return record

    @classmethod
    def get_recent(cls, count: int = 50) -> list[dict]:
        """Retrieve recent N audit log records."""
        if not AUDIT_LOG_FILE.exists():
            return []
        records = []
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-count:]:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            logger.exception("Boot critical exception encountered in guardian/audit_log.py")
            raise e
        return records
