# guardian/kill_switch.py — Emergency Pause & Kill Switch
"""
Global Emergency Pause Switch for Autonomous Operations.
Monitors flag files, CLI pause triggers, and hotkeys.
"""
from __future__ import annotations

import os
from pathlib import Path

PAUSED_FLAG_FILE = Path(__file__).resolve().parent / "PAUSED"


class KillSwitch:
    """Thread-safe kill switch & pause controller for BR JARVIS."""

    @classmethod
    def is_paused(cls) -> bool:
        """Check if autonomous operations are paused."""
        if PAUSED_FLAG_FILE.exists():
            return True
        if os.environ.get("JARVIS_PAUSED", "").strip().lower() in ("1", "true", "yes"):
            return True
        return False

    @classmethod
    def pause(cls, reason: str = "User initiated pause") -> bool:
        """Activate global pause."""
        try:
            PAUSED_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
            PAUSED_FLAG_FILE.write_text(f"PAUSED: {reason}\n", encoding="utf-8")
            return True
        except Exception:
            return False

    @classmethod
    def resume(cls) -> bool:
        """Resume autonomous operations."""
        try:
            if PAUSED_FLAG_FILE.exists():
                PAUSED_FLAG_FILE.unlink()
            return True
        except Exception:
            return False

    @classmethod
    def get_pause_reason(cls) -> str:
        """Get reason for active pause."""
        if PAUSED_FLAG_FILE.exists():
            try:
                return PAUSED_FLAG_FILE.read_text(encoding="utf-8").strip()
            except Exception:
                return "Flag file present"
        if os.environ.get("JARVIS_PAUSED"):
            return "Environment variable JARVIS_PAUSED set"
        return "Not paused"
