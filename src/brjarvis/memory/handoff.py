# memory/handoff.py — Cross-Session and Cross-Agent Handoff Store
"""
First-class Handoff objects for BR JARVIS.

A Handoff is a structured record of everything a new session or agent needs
to continue work without losing context. It closes the cross-session continuity
gap identified in the Phase 0 forensic audit.

Architecture:
  Handoffs are persisted in the `handoffs` table in jarvis_canonical.db.
  They are created at session end (or on demand) and consumed at session start.
  Once consumed, status transitions: OPEN -> CLAIMED -> DELIVERED.

Usage:
  from brjarvis.memory.handoff import create_handoff, claim_handoff, deliver_handoff

  # At end of a productive session:
  hnd = create_handoff(
      session_id=session_id,
      goal="Refactor memory architecture",
      completed=["Fixed vector_store.py", "Fixed memory_tools.py"],
      current_state="consolidator.py is next",
      next_steps=["Fix decay.py", "Wire context engine"],
  )

  # At start of next session:
  hnd = claim_handoff(agent_id="jarvis")
  if hnd:
      # resume from hnd.goal, hnd.next_steps, etc.
      deliver_handoff(hnd.handoff_id)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import List, Optional

from .canonical_db import get_canonical_db
from .domain import Handoff, HandoffStatus

logger = logging.getLogger("JARVIS.HandoffStore")


class HandoffStore:
    """CRUD store for Handoff objects persisted in canonical DB."""

    def __init__(self):
        self.db = get_canonical_db()

    def create(self, handoff: Handoff) -> Handoff:
        """Persist a new Handoff."""
        with self.db._lock:
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO handoffs (
                        handoff_id, session_id, project_id, source_agent, target_agent,
                        created_at, expires_at, goal,
                        completed_json, current_state, failed_attempts_json,
                        decisions_json, open_questions_json, next_steps_json,
                        important_files_json, risks_json, confidence,
                        status, reusable, claimed_by, claimed_at, delivered_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        handoff.handoff_id,
                        handoff.session_id,
                        handoff.project_id,
                        handoff.source_agent,
                        handoff.target_agent,
                        handoff.created_at,
                        handoff.expires_at,
                        handoff.goal,
                        json.dumps(handoff.completed),
                        handoff.current_state,
                        json.dumps(handoff.failed_attempts),
                        json.dumps(handoff.decisions),
                        json.dumps(handoff.open_questions),
                        json.dumps(handoff.next_steps),
                        json.dumps(handoff.important_files),
                        json.dumps(handoff.risks),
                        handoff.confidence,
                        handoff.status.value,
                        1 if handoff.reusable else 0,
                        handoff.claimed_by,
                        handoff.claimed_at,
                        handoff.delivered_at,
                    ),
                )
                conn.commit()
        logger.info("[HandoffStore] Created handoff %s", handoff.handoff_id)
        return handoff

    def get(self, handoff_id: str) -> Optional[Handoff]:
        """Fetch a single Handoff by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,))
            row = cursor.fetchone()
            return self._row_to_handoff(row) if row else None

    def list_open(self, project_id: Optional[str] = None, target_agent: str = "") -> List[Handoff]:
        """Return all open handoffs, optionally filtered by project and agent."""
        now = time.time()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if project_id:
                cursor.execute(
                    """SELECT * FROM handoffs WHERE status = 'OPEN' AND project_id = ?
                       AND (target_agent = '' OR target_agent = ?)
                       AND (expires_at IS NULL OR expires_at > ?) ORDER BY created_at DESC""",
                    (project_id, target_agent, now),
                )
            else:
                cursor.execute(
                    """SELECT * FROM handoffs WHERE status = 'OPEN'
                       AND (target_agent = '' OR target_agent = ?)
                       AND (expires_at IS NULL OR expires_at > ?) ORDER BY created_at DESC""",
                    (target_agent, now),
                )
            return [self._row_to_handoff(r) for r in cursor.fetchall()]

    def get_latest_for_session(self, session_id: str) -> Optional[Handoff]:
        """Return the most recent handoff for a session."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM handoffs WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            )
            row = cursor.fetchone()
            return self._row_to_handoff(row) if row else None

    def update_status(self, handoff_id: str, status: HandoffStatus, **kwargs) -> bool:
        """Update status and optional fields."""
        with self.db._lock:
            with self.db.get_connection() as conn:
                set_clauses = ["status = ?"]
                params: list = [status.value]
                for field, value in kwargs.items():
                    set_clauses.append(f"{field} = ?")
                    params.append(value)
                params.append(handoff_id)
                conn.execute(
                    f"UPDATE handoffs SET {', '.join(set_clauses)} WHERE handoff_id = ?",
                    params,
                )
                conn.commit()
                return conn.total_changes > 0

    def claim(self, handoff_id: str, agent_id: str) -> Optional[Handoff]:
        """Claim a handoff. Returns updated Handoff or None."""
        hnd = self.get(handoff_id)
        if not hnd:
            return None
        if not hnd.claim(agent_id):
            logger.warning("[HandoffStore] Cannot claim %s (status=%s)", handoff_id, hnd.status.value)
            return None
        self.update_status(handoff_id, HandoffStatus.CLAIMED, claimed_by=agent_id, claimed_at=time.time())
        logger.info("[HandoffStore] Handoff %s claimed by %s", handoff_id, agent_id)
        return self.get(handoff_id)

    def deliver(self, handoff_id: str) -> bool:
        """Mark a handoff as delivered."""
        ok = self.update_status(handoff_id, HandoffStatus.DELIVERED, delivered_at=time.time())
        if ok:
            logger.info("[HandoffStore] Handoff %s delivered", handoff_id)
        return ok

    def expire_stale(self) -> int:
        """Mark expired handoffs. Returns count expired."""
        now = time.time()
        with self.db._lock:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE handoffs SET status = 'EXPIRED' WHERE status = 'OPEN' AND expires_at IS NOT NULL AND expires_at <= ?",
                    (now,),
                )
                conn.commit()
                count = cursor.rowcount
        if count:
            logger.info("[HandoffStore] Expired %d stale handoffs", count)
        return count

    @staticmethod
    def _row_to_handoff(row) -> Handoff:
        d = dict(row)

        def _jlist(key: str) -> list:
            raw = d.get(key, "[]")
            if isinstance(raw, list):
                return raw
            try:
                return json.loads(raw or "[]")
            except Exception:
                return []

        return Handoff(
            handoff_id=d.get("handoff_id", f"hnd_{uuid.uuid4().hex[:10]}"),
            session_id=d.get("session_id", ""),
            project_id=d.get("project_id", "global"),
            source_agent=d.get("source_agent", "jarvis"),
            target_agent=d.get("target_agent", ""),
            created_at=float(d.get("created_at", time.time())),
            expires_at=d.get("expires_at"),
            goal=d.get("goal", ""),
            completed=_jlist("completed_json"),
            current_state=d.get("current_state", ""),
            failed_attempts=_jlist("failed_attempts_json"),
            decisions=_jlist("decisions_json"),
            open_questions=_jlist("open_questions_json"),
            next_steps=_jlist("next_steps_json"),
            important_files=_jlist("important_files_json"),
            risks=_jlist("risks_json"),
            confidence=float(d.get("confidence", 1.0)),
            status=HandoffStatus(d.get("status", "OPEN")),
            reusable=bool(d.get("reusable", 0)),
            claimed_by=d.get("claimed_by", ""),
            claimed_at=d.get("claimed_at"),
            delivered_at=d.get("delivered_at"),
        )


_GLOBAL_HANDOFF_STORE: Optional[HandoffStore] = None


def get_handoff_store() -> HandoffStore:
    """Return the global HandoffStore singleton."""
    global _GLOBAL_HANDOFF_STORE
    if _GLOBAL_HANDOFF_STORE is None:
        _GLOBAL_HANDOFF_STORE = HandoffStore()
    return _GLOBAL_HANDOFF_STORE


def create_handoff(
    session_id: str,
    goal: str,
    completed: Optional[List[str]] = None,
    current_state: str = "",
    failed_attempts: Optional[List[str]] = None,
    decisions: Optional[List[str]] = None,
    open_questions: Optional[List[str]] = None,
    next_steps: Optional[List[str]] = None,
    important_files: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
    project_id: str = "global",
    source_agent: str = "jarvis",
    target_agent: str = "",
    confidence: float = 1.0,
    expires_in_hours: Optional[float] = None,
) -> Handoff:
    """Create and persist a new handoff."""
    expires_at = (time.time() + expires_in_hours * 3600) if expires_in_hours else None
    hnd = Handoff(
        session_id=session_id,
        goal=goal,
        completed=completed or [],
        current_state=current_state,
        failed_attempts=failed_attempts or [],
        decisions=decisions or [],
        open_questions=open_questions or [],
        next_steps=next_steps or [],
        important_files=important_files or [],
        risks=risks or [],
        project_id=project_id,
        source_agent=source_agent,
        target_agent=target_agent,
        confidence=confidence,
        expires_at=expires_at,
    )
    return get_handoff_store().create(hnd)


def claim_handoff(agent_id: str = "jarvis", project_id: Optional[str] = None) -> Optional[Handoff]:
    """Claim the most recent open handoff. Returns None if none available."""
    store = get_handoff_store()
    store.expire_stale()
    open_handoffs = store.list_open(project_id=project_id, target_agent=agent_id)
    if not open_handoffs:
        open_handoffs = store.list_open(project_id=project_id, target_agent="")
    if not open_handoffs:
        return None
    return store.claim(open_handoffs[0].handoff_id, agent_id)


def deliver_handoff(handoff_id: str) -> bool:
    """Mark a handoff as delivered after successful resumption."""
    return get_handoff_store().deliver(handoff_id)


def get_latest_handoff_for_session(session_id: str) -> Optional[Handoff]:
    """Get the most recent handoff for a session."""
    return get_handoff_store().get_latest_for_session(session_id)
