# agent/session.py — Canonical Stateful AgentSession Model
"""
Canonical Agent Session state model for BR JARVIS.
The single authoritative state container shared across CLI, Web, Voice, Desktop, and API clients.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from brjarvis.contracts.session import SessionState
from brjarvis.core.paths import paths
from brjarvis.events.bus import get_event_bus
from brjarvis.events.types import SessionLifecycleEvent
from brjarvis.memory.canonical_db import get_canonical_db
from brjarvis.security.permission_request import (
    PermissionDecision,
    PermissionManager,
    PermissionRequest,
    get_permission_manager,
)

logger = logging.getLogger("JARVIS.AgentSession")


@dataclass
class SessionTurn:
    turn_id: str = field(default_factory=lambda: f"turn-{uuid.uuid4().hex[:8]}")
    role: str = "user"  # user, assistant, system, tool
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    backend: str = "gemini"
    latency_ms: int = 0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_evidence: Optional[str] = None
    correlation_id: str = "sys-event"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentSession:
    """The canonical stateful agent session unit for BR JARVIS."""
    session_id: str = field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:8]}")
    session_name: str = ""
    working_directory: str = field(default_factory=lambda: str(paths.PROJECT_ROOT))
    user_id: str = "default_user"
    device_id: str = "pc_primary"
    active_model: str = "gemini"
    model_strategy: str = "fixed"  # fixed | adaptive
    permission_mode: str = "confirm_destructive"
    current_mode: str = "general"
    current_state: str = "ACTIVE"  # NEW, ACTIVE, WAITING, PAUSED, COMPACTING, RESUMING, COMPLETED, FAILED, CANCELLED

    # Turn & history collections
    turns: List[SessionTurn] = field(default_factory=list)
    active_task_id: Optional[str] = None
    active_task_label: Optional[str] = None
    task_history: List[Dict[str, Any]] = field(default_factory=list)
    active_plan: Optional[Dict[str, Any]] = None
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    discovered_context: List[str] = field(default_factory=list)
    memory_references: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    verification_results: List[Dict[str, Any]] = field(default_factory=list)

    # Runtime state flags
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    correlation_id: str = field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:8]}")
    is_interrupted: bool = False
    is_cancelled: bool = False
    is_closed: bool = False

    def __post_init__(self):
        # Register in PermissionManager or publish session.started
        self._publish_session_event("started")
        self.save_to_store()

    def _publish_session_event(self, action: str) -> None:
        try:
            get_event_bus().publish(SessionLifecycleEvent(
                topic=f"session.{action}",
                session_id=self.session_id,
                action=action,
                mode=self.current_mode,
                active_model=self.active_model,
                turns_count=len(self.turns),
                correlation_id=self.correlation_id,
            ))
        except Exception as e:
            logger.debug("Session event emission note: %s", e)

    # ── Turn Management ────────────────────────────────────────────────────────

    def add_user_turn(self, content: str) -> SessionTurn:
        turn = SessionTurn(
            role="user",
            content=content,
            backend=self.active_model,
            correlation_id=self.correlation_id,
        )
        self.turns.append(turn)
        self.updated_at = time.time()
        return turn

    def add_assistant_turn(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        verification_evidence: Optional[str] = None,
        latency_ms: int = 0,
        backend: Optional[str] = None,
    ) -> SessionTurn:
        turn = SessionTurn(
            role="assistant",
            content=content,
            backend=backend or self.active_model,
            latency_ms=latency_ms,
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
            verification_evidence=verification_evidence,
            correlation_id=self.correlation_id,
        )
        self.turns.append(turn)
        self.updated_at = time.time()
        return turn

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Return formatted conversation history for model context."""
        res = []
        for t in self.turns[-limit:]:
            res.append({"role": t.role, "content": t.content})
        return res

    # ── Tool & Verification Tracking ───────────────────────────────────────────

    def record_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        duration_ms: float = 0.0,
        verified: bool = False,
        error: Optional[str] = None,
        step_id: str = "",
    ) -> None:
        rec = {
            "tool_name": tool_name,
            "args": args,
            "result": str(result)[:3000],
            "duration_ms": duration_ms,
            "verified": verified,
            "error": error,
            "step_id": step_id,
            "timestamp": time.time(),
        }
        self.tool_history.append(rec)
        self.updated_at = time.time()

    def record_verification(
        self,
        tool_name: str,
        target: str,
        verified: bool,
        evidence: str = "",
        error: Optional[str] = None,
    ) -> None:
        rec = {
            "tool_name": tool_name,
            "target": target,
            "verified": verified,
            "evidence": evidence,
            "error": error,
            "timestamp": time.time(),
        }
        self.verification_results.append(rec)
        self.updated_at = time.time()

    def record_artifact(self, artifact_info: Dict[str, Any]) -> None:
        self.artifacts.append(artifact_info)
        self.updated_at = time.time()

    # ── Task & Plan Management ────────────────────────────────────────────────

    def set_active_task(self, task_id: str, label: str) -> None:
        self.active_task_id = task_id
        self.active_task_label = label
        self.updated_at = time.time()

    def clear_active_task(self) -> None:
        if self.active_task_id:
            self.task_history.append({
                "task_id": self.active_task_id,
                "label": self.active_task_label,
                "completed_at": time.time(),
            })
        self.active_task_id = None
        self.active_task_label = None
        self.updated_at = time.time()

    def set_plan(self, plan: Dict[str, Any]) -> None:
        self.active_plan = plan
        self.updated_at = time.time()

    def update_plan_step(self, step_num: int, status: str, result: str = "") -> None:
        if not self.active_plan:
            return
        steps = self.active_plan.get("steps", [])
        for s in steps:
            if s.get("step") == step_num:
                s["status"] = status
                s["result"] = result
                break
        self.updated_at = time.time()

    def add_plan_step(self, description: str, tool: str = "agent_task") -> int:
        """Dynamically append a step to the active plan."""
        if not self.active_plan:
            self.active_plan = {"goal": "Dynamic Plan", "steps": []}
        steps = self.active_plan.setdefault("steps", [])
        new_step_num = len(steps) + 1
        steps.append({
            "step": new_step_num,
            "description": description,
            "tool": tool,
            "status": "pending",
        })
        self.updated_at = time.time()
        return new_step_num

    def remove_plan_step(self, step_num: int) -> bool:
        """Remove a pending step from the active plan."""
        if not self.active_plan or "steps" not in self.active_plan:
            return False
        steps = self.active_plan["steps"]
        original_len = len(steps)
        self.active_plan["steps"] = [s for s in steps if s.get("step") != step_num]
        self.updated_at = time.time()
        return len(self.active_plan["steps"]) < original_len

    def mark_step_blocked(self, step_num: int, reason: str = "") -> None:
        """Mark a plan step as blocked by dependency or policy."""
        self.update_plan_step(step_num, status="blocked", result=reason)

    def retry_step(self, step_num: int) -> None:
        """Reset a failed step back to pending for retry."""
        self.update_plan_step(step_num, status="pending", result="")

    # ── Model & Permission Control ────────────────────────────────────────────

    def switch_model(self, model_name: str, strategy: str = "fixed") -> None:
        self.active_model = model_name
        self.model_strategy = strategy
        self.updated_at = time.time()
        self._publish_session_event("model_switched")

    def set_permission_mode(self, mode: str) -> None:
        self.permission_mode = mode.lower()
        self.updated_at = time.time()

    def request_permission(
        self,
        tool: str,
        args: Dict[str, Any],
        reason: str = "",
    ) -> PermissionRequest:
        mgr = get_permission_manager()
        req = mgr.create_request(
            tool=tool,
            args=args,
            session_id=self.session_id,
            task_id=self.active_task_id or "default",
            reason=reason,
        )
        self.approvals.append(req.to_dict())
        return req

    # ── Lifecycle & Persistence ───────────────────────────────────────────────

    # ── Lifecycle, State Machine & Checkpointing ──────────────────────────────

    def transition_state(self, new_state: Union[str, SessionState]) -> None:
        """Explicit session state machine transition."""
        state_str = new_state.value if hasattr(new_state, "value") else str(new_state).upper()
        self.current_state = state_str
        self.updated_at = time.time()
        self._publish_session_event(f"state_changed_{state_str.lower()}")
        self.save_to_store()

    def checkpoint(self, snapshot_name: str = "") -> str:
        """Create a durable point-in-time session checkpoint in SQLite WAL database."""
        self.save_to_store()
        ckpt_id = f"ckpt-{uuid.uuid4().hex[:8]}"
        snapshot_data = self.to_dict()
        snapshot_data["snapshot_name"] = snapshot_name
        ckpt_rec = {
            "checkpoint_id": ckpt_id,
            "session_id": self.session_id,
            "state": self.current_state,
            "turn_index": len(self.turns),
            "active_task_id": self.active_task_id,
            "snapshot_data": snapshot_data,
            "created_at": time.time(),
        }
        try:
            get_canonical_db().save_session_checkpoint_record(ckpt_rec)
        except Exception as e:
            logger.error("Session checkpoint note: %s", e, exc_info=True)
        return ckpt_id

    def resume_from_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """Restore session state from the most recent or specified checkpoint."""
        try:
            db = get_canonical_db()
            ckpts = db.get_session_checkpoints(self.session_id)
            if not ckpts:
                return False
            target_ckpt = None
            if checkpoint_id:
                for c in ckpts:
                    if c.get("checkpoint_id") == checkpoint_id:
                        target_ckpt = c
                        break
            else:
                target_ckpt = ckpts[-1]

            if not target_ckpt or "snapshot_data" not in target_ckpt:
                return False

            data = target_ckpt["snapshot_data"]
            restored = AgentSession.from_dict(data)
            self.turns = restored.turns
            self.active_task_id = restored.active_task_id
            self.active_task_label = restored.active_task_label
            self.active_plan = restored.active_plan
            self.tool_history = restored.tool_history
            self.approvals = restored.approvals
            self.current_state = "RESUMING"
            self.updated_at = time.time()
            self.transition_state(SessionState.ACTIVE)
            return True
        except Exception as e:
            logger.error("Failed to resume session from checkpoint: %s", e)
            return False

    def pause(self, reason: str = "") -> None:
        """Pause active session and capture state checkpoint."""
        self.checkpoint(snapshot_name=f"paused: {reason}")
        self.transition_state(SessionState.PAUSED)

    def resume_session(self) -> None:
        """Resume a paused or waiting session."""
        self.transition_state(SessionState.ACTIVE)

    def cancel(self, reason: str = "") -> None:
        """Cancel active session and record cancellation reason."""
        self.is_cancelled = True
        if reason:
            self.errors.append({"type": "session_cancelled", "reason": reason, "time": time.time()})
        self.transition_state(SessionState.CANCELLED)

    def compact(self, summary: str, retain_last: int = 4) -> None:
        """Compact conversation history into a structured summary while preserving recent turns."""
        self.transition_state(SessionState.COMPACTING)
        if len(self.turns) > retain_last:
            retained = self.turns[-retain_last:]
            summary_turn = SessionTurn(
                role="system",
                content=f"[Session Compaction Summary]: {summary}",
                backend=self.active_model,
                correlation_id=self.correlation_id,
            )
            self.turns = [summary_turn] + retained
            self.discovered_context.append(f"Compacted at {time.strftime('%Y-%m-%d %H:%M:%S')}: {summary}")
        self.checkpoint(snapshot_name="post_compaction")
        self.transition_state(SessionState.ACTIVE)

    def create_handoff(
        self,
        target_agent: str,
        goal: str,
        next_steps: Optional[List[str]] = None,
        important_files: Optional[List[str]] = None,
        risks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a durable cross-agent handoff record."""
        hoff_id = f"hoff-{uuid.uuid4().hex[:8]}"
        completed = [t.content[:100] for t in self.turns if t.role == "assistant"]
        hoff_packet = {
            "handoff_id": hoff_id,
            "session_id": self.session_id,
            "source_agent": self.user_id,
            "target_agent": target_agent,
            "project_id": self.working_directory,
            "goal": goal,
            "completed": completed[-5:],
            "current_state": self.current_state,
            "failed_attempts": [e.get("reason", str(e)) for e in self.errors],
            "decisions": [t.content[:120] for t in self.turns if "decision" in t.content.lower()],
            "open_questions": [],
            "next_steps": next_steps or [],
            "important_files": important_files or [],
            "risks": risks or [],
            "confidence": 1.0,
            "created_at": time.time(),
            "expires_at": time.time() + 86400.0,
        }
        self.checkpoint(snapshot_name=f"handoff_to_{target_agent}")
        return hoff_packet

    def close(self, consolidate: bool = True) -> None:
        if self.is_closed:
            return
        self.is_closed = True
        self.current_state = "COMPLETED"
        self.updated_at = time.time()
        self._publish_session_event("closed")
        self.save_to_store()

    def save_to_store(self) -> None:
        """Persist session state directly to authoritative Canonical SQLite WAL DB."""
        try:
            get_canonical_db().save_session_record(self.to_dict())
        except Exception as e:
            logger.debug("Session canonical DB persistence note: %s", e)
        try:
            from brjarvis.history.session_store import SessionStore
            store = SessionStore()
            store.save_session(self.session_id, self.to_dict())
        except Exception:
            pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "working_directory": self.working_directory,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "active_model": self.active_model,
            "model_strategy": self.model_strategy,
            "permission_mode": self.permission_mode,
            "current_mode": self.current_mode,
            "current_state": self.current_state,
            "turns": [t.to_dict() for t in self.turns],
            "active_task_id": self.active_task_id,
            "active_task_label": self.active_task_label,
            "task_history": self.task_history,
            "active_plan": self.active_plan,
            "tool_history": self.tool_history,
            "approvals": self.approvals,
            "discovered_context": self.discovered_context,
            "memory_references": self.memory_references,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "verification_results": self.verification_results,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "correlation_id": self.correlation_id,
            "is_interrupted": self.is_interrupted,
            "is_cancelled": self.is_cancelled,
            "is_closed": self.is_closed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentSession:
        data_copy = dict(data)
        turns_raw = data_copy.pop("turns", [])
        session = cls(**{k: v for k, v in data_copy.items() if k in cls.__dataclass_fields__})
        session.turns = [SessionTurn(**t) for t in turns_raw if isinstance(t, dict)]
        return session


# Session registry for multi-session support
_SESSION_CACHE: Dict[str, AgentSession] = {}


def get_or_create_session(
    session_id: Optional[str] = None,
    mode: str = "general",
    model: str = "gemini",
) -> AgentSession:
    """Retrieve existing active session or instantiate a new canonical AgentSession."""
    global _SESSION_CACHE
    if session_id and session_id in _SESSION_CACHE:
        return _SESSION_CACHE[session_id]

    # Check authoritative canonical SQLite WAL DB first
    if session_id:
        try:
            saved = get_canonical_db().get_session_record(session_id)
            if saved:
                sess = AgentSession.from_dict(saved)
                _SESSION_CACHE[session_id] = sess
                return sess
        except Exception:
            pass

    # Check secondary persistent store if needed
    if session_id:
        try:
            from brjarvis.history.session_store import SessionStore
            store = SessionStore()
            saved = store.get_session(session_id)
            if saved:
                sess = AgentSession.from_dict(saved)
                _SESSION_CACHE[session_id] = sess
                return sess
        except Exception:
            pass

    new_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
    sess = AgentSession(
        session_id=new_id,
        current_mode=mode,
        active_model=model,
    )
    sess.save_to_store()
    _SESSION_CACHE[new_id] = sess
    return sess


def list_active_sessions() -> List[AgentSession]:
    return list(_SESSION_CACHE.values())


def list_sessions() -> List[AgentSession]:
    return list_active_sessions()


def get_session(session_id: str) -> Optional[AgentSession]:
    return _SESSION_CACHE.get(session_id)


def delete_session(session_id: str) -> bool:
    if session_id in _SESSION_CACHE:
        del _SESSION_CACHE[session_id]
    try:
        get_canonical_db().delete_session_record(session_id)
    except Exception:
        pass
    return True


def reset_active_session() -> None:
    _SESSION_CACHE.clear()

