# memory/store.py — Authoritative Canonical Memory Storage Engine
"""
Canonical Memory Store for BR JARVIS.
Direct repository providing transactional CRUD operations, version control,
temporal state inspection, and consistency guarantees over SQLite WAL storage.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .canonical_db import CanonicalDatabaseManager, get_canonical_db
from .domain import CanonicalMemory, MemoryStatus, MemoryType, SourceType

logger = logging.getLogger("JARVIS.CanonicalStore")


class CanonicalMemoryStore:
    """Authoritative Memory Repository over Canonical SQLite WAL Database."""

    def __init__(self, db_manager: Optional[CanonicalDatabaseManager] = None):
        self.db = db_manager or get_canonical_db()
        self._lock = threading.RLock()
        self._derived_invalidation_hooks: List[Callable[[str, Optional[str]], None]] = []

    def register_invalidation_hook(self, hook: Callable[[str, Optional[str]], None]) -> None:
        """Register a callback for when memories are inserted/updated/deleted to invalidate caches/vector indexes."""
        self._derived_invalidation_hooks.append(hook)

    def _notify_invalidation(self, memory_id: str, content: Optional[str] = None) -> None:
        for hook in self._derived_invalidation_hooks:
            try:
                hook(memory_id, content)
            except Exception as e:
                logger.debug("Derived invalidation hook error: %s", e)

    def save(self, memory: CanonicalMemory) -> CanonicalMemory:
        """Insert or update a canonical memory record."""
        with self._lock:
            with self.db.get_connection() as conn:
                memory.updated_at = time.time()
                tags_str = json.dumps(memory.tags)
                conn.execute(
                    """
                    INSERT INTO canonical_memories (
                        memory_id, user_id, project_id, scope, namespace, memory_type,
                        entity, attribute, value, content, source_type, source_id, evidence,
                        confidence, reliability, importance, created_at, observed_at,
                        effective_from, effective_until, updated_at, last_accessed_at,
                        last_validated_at, status, version, supersedes_memory_id,
                        superseded_by_memory_id, conflict_group_id, session_id, task_id,
                        decision_id, tags_json, content_hash, embedding_id
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                    ON CONFLICT(memory_id) DO UPDATE SET
                        user_id = excluded.user_id,
                        project_id = excluded.project_id,
                        scope = excluded.scope,
                        namespace = excluded.namespace,
                        memory_type = excluded.memory_type,
                        entity = excluded.entity,
                        attribute = excluded.attribute,
                        value = excluded.value,
                        content = excluded.content,
                        source_type = excluded.source_type,
                        source_id = excluded.source_id,
                        evidence = excluded.evidence,
                        confidence = excluded.confidence,
                        reliability = excluded.reliability,
                        importance = excluded.importance,
                        effective_from = excluded.effective_from,
                        effective_until = excluded.effective_until,
                        updated_at = excluded.updated_at,
                        last_accessed_at = excluded.last_accessed_at,
                        last_validated_at = excluded.last_validated_at,
                        status = excluded.status,
                        version = excluded.version,
                        supersedes_memory_id = excluded.supersedes_memory_id,
                        superseded_by_memory_id = excluded.superseded_by_memory_id,
                        conflict_group_id = excluded.conflict_group_id,
                        session_id = excluded.session_id,
                        task_id = excluded.task_id,
                        decision_id = excluded.decision_id,
                        tags_json = excluded.tags_json,
                        content_hash = excluded.content_hash,
                        embedding_id = excluded.embedding_id
                    """,
                    (
                        memory.memory_id, memory.user_id, memory.project_id, memory.scope,
                        memory.namespace, memory.memory_type.value, memory.entity,
                        memory.attribute, str(memory.value) if memory.value is not None else "",
                        memory.content, memory.source_type.value, memory.source_id,
                        memory.evidence, memory.confidence, memory.reliability,
                        memory.importance, memory.created_at, memory.observed_at,
                        memory.effective_from, memory.effective_until, memory.updated_at,
                        memory.last_accessed_at, memory.last_validated_at, memory.status.value,
                        memory.version, memory.supersedes_memory_id, memory.superseded_by_memory_id,
                        memory.conflict_group_id, memory.session_id, memory.task_id,
                        memory.decision_id, tags_str, memory.content_hash, memory.embedding_id
                    ),
                )
                conn.commit()

            self._notify_invalidation(memory.memory_id, memory.content)
            return memory

    def get(self, memory_id: str) -> Optional[CanonicalMemory]:
        """Fetch a canonical memory record by its primary key."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM canonical_memories WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_memory(row)

    def get_by_entity_attribute(
        self,
        entity: str,
        attribute: str,
        project_id: str = "global",
        scope: str = "user",
        status: MemoryStatus = MemoryStatus.ACTIVE,
    ) -> Optional[CanonicalMemory]:
        """Retrieve the active memory matching an entity and attribute."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM canonical_memories
                WHERE entity = ? AND attribute = ? AND project_id = ? AND scope = ? AND status = ?
                ORDER BY version DESC, updated_at DESC LIMIT 1
                """,
                (entity, attribute, project_id, scope, status.value),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_memory(row)

    def list_active(
        self,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        scope: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
    ) -> List[CanonicalMemory]:
        """List all currently active records with optional project/scope/type filtering."""
        query = "SELECT * FROM canonical_memories WHERE status = 'ACTIVE' AND user_id = ?"
        params: List[Any] = [user_id]

        if project_id is not None:
            query += " AND (project_id = ? OR project_id = 'global')"
            params.append(project_id)
        if scope is not None:
            query += " AND scope = ?"
            params.append(scope)
        if memory_type is not None:
            query += " AND memory_type = ?"
            params.append(memory_type.value)

        query += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def list_all(
        self,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[CanonicalMemory]:
        """List all records (including superseded and archived)."""
        query = "SELECT * FROM canonical_memories WHERE user_id = ?"
        params: List[Any] = [user_id]
        if project_id is not None:
            query += " AND (project_id = ? OR project_id = 'global')"
            params.append(project_id)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def list_history(self, entity: str, attribute: str) -> List[CanonicalMemory]:
        """Retrieve full audit history chain for an entity-attribute pair."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM canonical_memories
                WHERE entity = ? AND attribute = ?
                ORDER BY version ASC, created_at ASC
                """,
                (entity, attribute),
            )
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def supersede(self, old_memory_id: str, new_memory: CanonicalMemory) -> CanonicalMemory:
        """Mark an old record as SUPERSEDED and atomically save the newer replacement."""
        with self._lock:
            old = self.get(old_memory_id)
            now = time.time()
            if old:
                old.mark_superseded(new_memory.memory_id, timestamp=now)
                self.save(old)
                new_memory.version = old.version + 1
                new_memory.supersedes_memory_id = old_memory_id
            new_memory.effective_from = now
            return self.save(new_memory)

    def delete(self, memory_id: str, hard: bool = False) -> bool:
        """Delete a memory record (soft-delete marks INVALID, hard-delete removes row)."""
        with self._lock:
            existing = self.get(memory_id)
            if not existing:
                return False

            with self.db.get_connection() as conn:
                if hard:
                    conn.execute("DELETE FROM canonical_memories WHERE memory_id = ?", (memory_id,))
                else:
                    conn.execute(
                        "UPDATE canonical_memories SET status = 'INVALID', updated_at = ? WHERE memory_id = ?",
                        (time.time(), memory_id),
                    )
                conn.commit()

            self._notify_invalidation(memory_id, existing.content)
            return True

    def delete_all(self, user_id: str = "default_user", project_id: Optional[str] = None) -> int:
        """Delete all memories for a given user or project."""
        with self._lock:
            with self.db.get_connection() as conn:
                if project_id:
                    cursor = conn.execute(
                        "DELETE FROM canonical_memories WHERE user_id = ? AND project_id = ?",
                        (user_id, project_id),
                    )
                else:
                    cursor = conn.execute(
                        "DELETE FROM canonical_memories WHERE user_id = ?",
                        (user_id,),
                    )
                count = cursor.rowcount
                conn.commit()

            self._notify_invalidation("*", None)
            return count

    def search_lexical(
        self,
        query: str,
        project_id: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 20,
    ) -> List[CanonicalMemory]:
        """Perform exact and lexical search over active memories."""
        terms = [t.strip().lower() for t in query.split() if len(t.strip()) >= 2]
        if not terms:
            return []

        q_sql = "SELECT * FROM canonical_memories WHERE status = 'ACTIVE'"
        params: List[Any] = []

        if project_id:
            q_sql += " AND (project_id = ? OR project_id = 'global')"
            params.append(project_id)
        if scope:
            q_sql += " AND scope = ?"
            params.append(scope)

        like_clauses = []
        for term in terms[:5]:
            like_clauses.append("(LOWER(content) LIKE ? OR LOWER(entity) LIKE ? OR LOWER(attribute) LIKE ? OR LOWER(value) LIKE ?)")
            p_val = f"%{term}%"
            params.extend([p_val, p_val, p_val, p_val])

        if like_clauses:
            q_sql += " AND (" + " OR ".join(like_clauses) + ")"

        q_sql += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(q_sql, tuple(params))
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def touch_accessed(self, memory_id: str) -> None:
        """Update last_accessed_at timestamp without changing updated_at."""
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE canonical_memories SET last_accessed_at = ? WHERE memory_id = ?",
                (time.time(), memory_id),
            )
            conn.commit()

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> CanonicalMemory:
        tags = []
        if "tags_json" in row.keys() and row["tags_json"]:
            try:
                tags = json.loads(row["tags_json"])
            except Exception:
                tags = []

        return CanonicalMemory(
            memory_id=row["memory_id"],
            user_id=row["user_id"],
            project_id=row["project_id"],
            scope=row["scope"],
            namespace=row["namespace"],
            memory_type=MemoryType.from_str(row["memory_type"]),
            entity=row["entity"] or "",
            attribute=row["attribute"] or "",
            value=row["value"] or "",
            content=row["content"],
            source_type=SourceType.from_str(row["source_type"]),
            source_id=row["source_id"] or "",
            evidence=row["evidence"] or "",
            confidence=float(row["confidence"]),
            reliability=float(row["reliability"]),
            importance=float(row["importance"]),
            created_at=float(row["created_at"]),
            observed_at=float(row["observed_at"]),
            effective_from=float(row["effective_from"]),
            effective_until=float(row["effective_until"]) if row["effective_until"] is not None else None,
            updated_at=float(row["updated_at"]),
            last_accessed_at=float(row["last_accessed_at"]),
            last_validated_at=float(row["last_validated_at"]),
            status=MemoryStatus(row["status"]),
            version=int(row["version"]),
            supersedes_memory_id=row["supersedes_memory_id"],
            superseded_by_memory_id=row["superseded_by_memory_id"],
            conflict_group_id=row["conflict_group_id"],
            session_id=row["session_id"] or "",
            task_id=row["task_id"] or "",
            decision_id=row["decision_id"] or "",
            tags=tags,
            content_hash=row["content_hash"] or "",
            embedding_id=row["embedding_id"],
        )


_GLOBAL_CANONICAL_STORE: Optional[CanonicalMemoryStore] = None


def get_canonical_store() -> CanonicalMemoryStore:
    """Return singleton CanonicalMemoryStore."""
    global _GLOBAL_CANONICAL_STORE
    if _GLOBAL_CANONICAL_STORE is None:
        _GLOBAL_CANONICAL_STORE = CanonicalMemoryStore()
    return _GLOBAL_CANONICAL_STORE
