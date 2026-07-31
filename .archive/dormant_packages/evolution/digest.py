# evolution/digest.py — Human Approval Change Digest
"""
Queues HIGH-risk patches for one-tap human approval or rejection.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

DIGEST_FILE = Path("workspace/logs/change_digest.json")


class ChangeDigest:
    """Manages queued HIGH-risk patch proposals requiring user approval."""

    @classmethod
    def queue_proposal(cls, proposal: dict) -> dict:
        """Add a proposal to the pending digest queue."""
        queue = cls.get_queued()
        proposal["queued_at"] = time.time()
        proposal["status"] = "PENDING"
        queue.append(proposal)
        cls._save_queued(queue)
        return proposal

    @classmethod
    def get_queued(cls) -> list[dict]:
        """Get all pending digest items."""
        if not DIGEST_FILE.exists():
            return []
        try:
            data = json.loads(DIGEST_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @classmethod
    def approve_proposal(cls, proposal_id: str) -> dict | None:
        """Mark a proposal as approved."""
        queue = cls.get_queued()
        for p in queue:
            if p.get("proposal_id") == proposal_id:
                p["status"] = "APPROVED"
                p["acted_at"] = time.time()
                cls._save_queued(queue)
                return p
        return None

    @classmethod
    def reject_proposal(cls, proposal_id: str) -> dict | None:
        """Mark a proposal as rejected."""
        queue = cls.get_queued()
        for p in queue:
            if p.get("proposal_id") == proposal_id:
                p["status"] = "REJECTED"
                p["acted_at"] = time.time()
                cls._save_queued(queue)
                return p
        return None

    @classmethod
    def _save_queued(cls, queue: list[dict]):
        DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        DIGEST_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")
