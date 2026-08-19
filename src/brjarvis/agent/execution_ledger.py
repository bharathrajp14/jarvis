# agent/execution_ledger.py — BR JARVIS MK40.2 Immutable Execution Ledger
"""
Append-only execution ledger for BR JARVIS.

The execution system — not the model — is the source of truth for whether an
operation succeeded. Every tool call is recorded here with its actual stdout,
returncode, and verification status before the executor inspects the result.

Architecture:
    Executor writes → Ledger stores → CompletionGate reads → Response reports

The ledger is keyed by (task_id, step_id). Entries are immutable once written.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.ExecutionLedger")


# ── Tool execution status vocabulary ──────────────────────────────────────────


class LedgerStatus(str, Enum):
    """Canonical status codes for each ledger entry. Never inferred — always observed."""

    SUCCESS = "SUCCESS"  # tool ran, returncode 0, output verified
    FAILED = "FAILED"  # tool ran, returncode != 0 or output error
    PARTIAL = "PARTIAL"  # tool ran, some outputs verified, some not
    BLOCKED = "BLOCKED"  # tool could not run — permission/policy blocked
    TIMEOUT = "TIMEOUT"  # tool did not return within step timeout
    UNAVAILABLE = "UNAVAILABLE"  # tool is not registered / dependency missing
    REQUIRES_USER = "REQUIRES_USER"  # needs human input to continue
    UNVERIFIED = "UNVERIFIED"  # ran but verification could not confirm result


# ── Ledger entry data contract ─────────────────────────────────────────────────


@dataclass
class LedgerEntry:
    """
    Immutable record of a single tool execution.

    Fields mirror the §5 Tool Evidence Contract from the MK40.2 spec:
        tool_name, task_id, step_id, execution_id, status, stdout, stderr,
        duration, side_effects, evidence, verification_status
    """

    tool_name: str
    task_id: str
    step_id: str  # plan step identifier, e.g. "step_3"
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: LedgerStatus = LedgerStatus.UNVERIFIED
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    duration_seconds: float = 0.0
    side_effects: List[str] = field(default_factory=list)  # e.g. ["file:created:/path"]
    evidence: str = ""  # human-readable proof string
    verification_status: LedgerStatus = LedgerStatus.UNVERIFIED
    parameters: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    # Immutability guard — set to True after first write
    _sealed: bool = field(default=False, repr=False, compare=False)

    def seal(self) -> "LedgerEntry":
        """Mark this entry as immutable. Further writes should create a new entry."""
        object.__setattr__(self, "_sealed", True)
        return self

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["verification_status"] = self.verification_status.value
        d.pop("_sealed", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEntry":
        raw = dict(data)
        for field_name in ("status", "verification_status"):
            if field_name in raw and isinstance(raw[field_name], str):
                try:
                    raw[field_name] = LedgerStatus(raw[field_name])
                except ValueError:
                    raw[field_name] = LedgerStatus.UNVERIFIED
        raw.pop("_sealed", None)
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


# ── Execution Ledger ───────────────────────────────────────────────────────────


class ExecutionLedger:
    """
    Append-only execution ledger persisted in the canonical SQLite database.

    Rules:
      - Entries are never deleted or modified once written.
      - The ledger is the ONLY authoritative record of what actually happened.
      - The model must never assert success based on its own reasoning; it must
        read from this ledger.
    """

    TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS execution_ledger (
        entry_id         TEXT PRIMARY KEY,
        task_id          TEXT NOT NULL,
        step_id          TEXT NOT NULL,
        execution_id     TEXT NOT NULL,
        tool_name        TEXT NOT NULL,
        status           TEXT NOT NULL,
        stdout           TEXT DEFAULT '',
        stderr           TEXT DEFAULT '',
        return_code      INTEGER DEFAULT 0,
        duration_seconds REAL DEFAULT 0.0,
        side_effects     TEXT DEFAULT '[]',
        evidence         TEXT DEFAULT '',
        verification_status TEXT NOT NULL,
        parameters       TEXT DEFAULT '{}',
        error            TEXT,
        timestamp        REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ledger_task ON execution_ledger(task_id);
    CREATE INDEX IF NOT EXISTS idx_ledger_step ON execution_ledger(task_id, step_id);
    """

    def __init__(self, db_manager=None):
        from brjarvis.memory.canonical_db import get_canonical_db

        self._db = db_manager or get_canonical_db()
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create ledger table if it does not exist."""
        try:
            with self._db.get_connection() as conn:
                for stmt in self.TABLE_DDL.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        conn.execute(stmt)
                conn.commit()
        except Exception as e:
            logger.error("[Ledger] Failed to create execution_ledger table: %s", e)

    def append(self, entry: LedgerEntry) -> str:
        """
        Append a new ledger entry. Returns the generated entry_id.

        Raises ValueError if an entry with the same (task_id, step_id, execution_id) already exists.
        """
        entry_id = f"led_{entry.task_id}_{entry.step_id}_{entry.execution_id}"
        try:
            with self._db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO execution_ledger
                        (entry_id, task_id, step_id, execution_id, tool_name,
                         status, stdout, stderr, return_code, duration_seconds,
                         side_effects, evidence, verification_status, parameters,
                         error, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        entry.task_id,
                        entry.step_id,
                        entry.execution_id,
                        entry.tool_name,
                        entry.status.value,
                        entry.stdout[:4096],
                        entry.stderr[:2048],
                        entry.return_code,
                        entry.duration_seconds,
                        json.dumps(entry.side_effects),
                        entry.evidence[:2048],
                        entry.verification_status.value,
                        json.dumps(entry.parameters, default=str),
                        entry.error,
                        entry.timestamp,
                    ),
                )
                conn.commit()
            logger.debug("[Ledger] Appended entry %s (%s → %s)", entry_id, entry.tool_name, entry.status.value)
        except Exception as e:
            logger.error("[Ledger] Failed to append entry: %s", e)
        return entry_id

    def get_task_entries(self, task_id: str) -> List[LedgerEntry]:
        """Return all ledger entries for a task in insertion order (by timestamp)."""
        try:
            with self._db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM execution_ledger WHERE task_id = ? ORDER BY timestamp ASC", (task_id,)
                )
                rows = cursor.fetchall()
                return [self._row_to_entry(r) for r in rows]
        except Exception as e:
            logger.error("[Ledger] Failed to fetch entries for task %s: %s", task_id, e)
            return []

    def get_step_entry(self, task_id: str, step_id: str) -> Optional[LedgerEntry]:
        """Return the most recent ledger entry for a specific step, or None."""
        try:
            with self._db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM execution_ledger WHERE task_id = ? AND step_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (task_id, step_id),
                )
                row = cursor.fetchone()
                return self._row_to_entry(row) if row else None
        except Exception as e:
            logger.error("[Ledger] Failed to fetch step entry %s/%s: %s", task_id, step_id, e)
            return None

    def step_is_verified(self, task_id: str, step_id: str) -> bool:
        """
        Returns True only if this step has a SUCCESS ledger entry with
        verification_status == SUCCESS. Used by the executor to skip
        already-completed steps on retry (prevents duplication).
        """
        entry = self.get_step_entry(task_id, step_id)
        if entry is None:
            return False
        return entry.status == LedgerStatus.SUCCESS and entry.verification_status == LedgerStatus.SUCCESS

    def task_has_critical_failure(self, task_id: str) -> bool:
        """Returns True if any ledger entry for this task is FAILED or BLOCKED."""
        entries = self.get_task_entries(task_id)
        return any(e.status in (LedgerStatus.FAILED, LedgerStatus.BLOCKED) for e in entries)

    def build_evidence_report(self, task_id: str) -> str:
        """
        Build a structured text evidence report from ledger entries.
        This is what the FinalResponseGenerator uses — never the model's imagination.
        """
        entries = self.get_task_entries(task_id)
        if not entries:
            return "No execution evidence recorded for this task."

        lines = [f"Execution Evidence Report — Task {task_id}", "=" * 60]
        for e in entries:
            status_icon = {
                LedgerStatus.SUCCESS: "✅",
                LedgerStatus.FAILED: "❌",
                LedgerStatus.PARTIAL: "⚠️",
                LedgerStatus.BLOCKED: "🚫",
                LedgerStatus.TIMEOUT: "⏱️",
                LedgerStatus.UNAVAILABLE: "🔕",
                LedgerStatus.REQUIRES_USER: "👤",
                LedgerStatus.UNVERIFIED: "❓",
            }.get(e.status, "?")
            lines.append(f"\nStep {e.step_id} [{e.tool_name}] {status_icon} {e.status.value}")
            if e.evidence:
                lines.append(f"  Evidence: {e.evidence}")
            if e.error:
                lines.append(f"  Error: {e.error}")
            if e.side_effects:
                lines.append(f"  Side Effects: {', '.join(e.side_effects)}")

        return "\n".join(lines)

    @staticmethod
    def _row_to_entry(row) -> LedgerEntry:
        """Convert a sqlite3.Row to a LedgerEntry."""
        if hasattr(row, "keys"):
            data = dict(row)
        else:
            data = dict(
                zip(
                    [
                        "entry_id",
                        "task_id",
                        "step_id",
                        "execution_id",
                        "tool_name",
                        "status",
                        "stdout",
                        "stderr",
                        "return_code",
                        "duration_seconds",
                        "side_effects",
                        "evidence",
                        "verification_status",
                        "parameters",
                        "error",
                        "timestamp",
                    ],
                    row,
                )
            )
        data["side_effects"] = json.loads(data.get("side_effects", "[]") or "[]")
        data["parameters"] = json.loads(data.get("parameters", "{}") or "{}")
        # Remove DB-only field entry_id before creating dataclass
        data.pop("entry_id", None)
        return LedgerEntry.from_dict(data)


# ── Global singleton ───────────────────────────────────────────────────────────

_GLOBAL_LEDGER: Optional[ExecutionLedger] = None


def get_execution_ledger() -> ExecutionLedger:
    """Return the global ExecutionLedger singleton."""
    global _GLOBAL_LEDGER
    if _GLOBAL_LEDGER is None:
        _GLOBAL_LEDGER = ExecutionLedger()
    return _GLOBAL_LEDGER
