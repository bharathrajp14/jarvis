# memory/unified_memory.py — Master Multi-Tier Memory Coordinator for JARVIS MK37
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from core.runtime import get_runtime
from events.bus import get_event_bus
from .archiver import MemoryArchiver
from .cache import MemoryCache
from .working import WorkingMemory
from .persistent_store import MemoryEntry, save_memory, search_memory, delete_memory, load_index
from .vector_store import VectorMemory
from .conversation_store import ConversationStore
from .experience_replay import ExperienceReplayStore, ExperienceTrajectory, get_experience_replay
from .lessons import LessonStore
from .reflection import ReflectionEngine

logger = logging.getLogger("JARVIS.UnifiedMemory")


class UnifiedMemoryManager:
    """
    Master Unified Memory Coordinator bringing together 7 tiers:
      L0: Immediate Scratchpad
      L1: Working Memory (Short-term context window)
      L2: Session Conversation Store (Turn logs)
      L3: Semantic Vector Memory (Embeddings)
      L4: Persistent Memory (Structured facts/preferences)
      L5: Document & Knowledge Graph RAG
      L6: Experience Replay & Lessons (Execution trajectory learning)
    """

    def __init__(self):
        self.working = WorkingMemory(max_tokens=100000)
        self.cache = MemoryCache(default_ttl=300.0)
        self.archiver = MemoryArchiver(max_age_days=30)
        self.vector = VectorMemory()
        self.conversations = ConversationStore()
        self.lessons = LessonStore()
        self.experience = get_experience_replay()
        self.reflection = ReflectionEngine(self.lessons)

        self.runtime = get_runtime()
        self.event_bus = get_event_bus()

        # Register self in DI Container
        self.runtime.container.register_instance(UnifiedMemoryManager, self)
        logger.info("⚡ UnifiedMemoryManager fully initialized across 7 hierarchical memory tiers")

    # ── Tier 1: Working Memory ─────────────────────────────────────────────

    def add_interaction(self, role: str, content: str) -> None:
        """Add turn to active working memory."""
        self.working.add(role, content)

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Retrieve active conversation history."""
        return self.working.get()

    def add_user_message(self, content: str) -> None:
        """Add user message to active working memory."""
        self.add_interaction("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to active working memory."""
        self.add_interaction("assistant", content)

    # ── Tier 2: Persistent & Semantic Vector Memory ──────────────────────

    def remember(
        self,
        name: str,
        content: str,
        description: str = "",
        mem_type: str = "user",
        scope: str = "user",
        confidence: float = 1.0,
    ) -> MemoryEntry:
        """Save a new memory entry across persistent storage and vector index."""
        from datetime import datetime
        entry = MemoryEntry(
            name=name,
            description=description or name,
            type=mem_type,
            content=content,
            created=datetime.now().strftime("%Y-%m-%d"),
            scope=scope,
            confidence=confidence,
            source="user",
        )
        save_memory(entry, scope=scope)
        self.vector.store(text=f"{name}: {content}", metadata={"name": name, "type": mem_type})
        logger.info(f"💾 Unified Memory saved: [{scope}] {name}")
        return entry

    def forget(self, name: str, scope: str = "user") -> None:
        """Delete a memory from persistent storage, vector index, and caches."""
        from memory.persistent_store import _SEARCH_CACHE
        delete_memory(name, scope=scope)
        # Clear all search caches so recall() doesn't serve stale results
        _SEARCH_CACHE.clear()
        # Clear vector memory recall cache
        try:
            from memory.vector_store import VectorMemory
            VectorMemory._RECALL_CACHE.clear()
            # Also try to remove by doc_id from chromadb if available
            if self.vector and self.vector._collection is not None:
                try:
                    self.vector._collection.delete(where={"name": name})
                except Exception:
                    pass
            # Remove from fallback text store
            if self.vector and self.vector._fallback is not None:
                self.vector._fallback.entries = [
                    e for e in self.vector._fallback.entries
                    if name.lower() not in e.get("text", "").lower()[:len(name)+5]
                ]
                self.vector._fallback._save()
        except Exception as ve:
            logger.debug("Vector cache clear on forget: %s", ve)
        logger.info(f"🗑️ Unified Memory deleted: [{scope}] {name}")

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search all memory tiers for query-relevant context with decay-aware ranking."""
        import time, math, os
        from pathlib import Path
        results = []
        now = time.time()
        q_lower = query.lower().strip()

        # 1. Search Persistent Markdown/SQLite memory (primary structured tier)
        persistent_hits = search_memory(query)
        for p in persistent_hits[:limit * 2]:
            mtime = getattr(p, 'mtime_s', 0)
            if not mtime and getattr(p, 'file_path', None):
                try:
                    mtime = os.path.getmtime(p.file_path)
                except Exception:
                    mtime = now
            if not mtime:
                mtime = now
            # Compute recency score (files modified recently rank higher)
            age_days = max(0, (now - mtime) / 86400)
            recency_score = math.exp(-age_days / 30)  # 30-day half-life
            exact_boost = 0.3 if q_lower and q_lower in (f"{p.name} {p.description} {p.content}").lower() else 0.0
            rank = p.confidence * (0.85 + 0.15 * recency_score) + exact_boost
            results.append({
                "source": "persistent",
                "name": p.name,
                "description": p.description,
                "content": p.content,
                "type": p.type,
                "confidence": p.confidence,
                "_rank": rank,
            })

        # 2. Search Lesson store (operational learnings)
        try:
            lesson_hits = self.lessons.get_relevant_lessons(query, limit=3)
            seen_topics = set()
            for l in lesson_hits:
                topic_key = l.get('topic', '')
                if topic_key in seen_topics:
                    continue
                seen_topics.add(topic_key)
                lesson_rank = 0.80 if q_lower and q_lower in (l.get('correction', '') + l.get('topic', '')).lower() else 0.65
                results.append({
                    "source": "lesson",
                    "name": f"Lesson: {l['topic']}",
                    "content": l['correction'],
                    "confidence": 0.85,
                    "_rank": lesson_rank,
                })
        except Exception:
            pass

        # 3. Semantic Vector Store — only when local results are insufficient
        if len(results) < limit and len(query.split()) >= 2:
            try:
                vector_hits = self.vector.recall(query, n=max(1, limit - len(results)))
                for v_text in vector_hits:
                    if not any(r.get("content", "") in v_text for r in results):
                        results.append({
                            "source": "vector",
                            "name": "Semantic Vector Memory",
                            "content": v_text,
                            "confidence": 0.75,
                            "_rank": 0.70,
                        })
            except Exception as v_err:
                logger.debug("Vector memory recall fallback: %s", v_err)

        # Sort by decay-aware rank descending
        results.sort(key=lambda r: r.get("_rank", 0.5), reverse=True)
        # Strip internal rank key before returning
        for r in results:
            r.pop("_rank", None)
        return results[:limit]

    # ── Tier 3: Tool Result Caching ────────────────────────────────────────

    def cache_tool_result(self, tool_name: str, args: Dict[str, Any], result: Any, ttl: Optional[float] = None) -> None:
        """Cache execution result of a tool call."""
        key = f"tool:{tool_name}:{str(args)}"
        self.cache.set(key, result, ttl=ttl)

    def get_cached_tool_result(self, tool_name: str, args: Dict[str, Any]) -> Optional[Any]:
        """Retrieve cached tool execution result if available."""
        key = f"tool:{tool_name}:{str(args)}"
        return self.cache.get(key)

    # ── Tier 4: Lessons & Reflection ──────────────────────────────────────

    def process_turn_reflection(self, user_input: str, previous_output: str, elapsed_sec: float = 0) -> Optional[Dict[str, Any]]:
        """Process turn for automatic self-correction and lesson learning."""
        return self.reflection.process_turn(user_input, previous_output, elapsed_sec)

    # ── Tier 5: Session Consolidation ─────────────────────────────────────

    def consolidate(self) -> None:
        """Trigger memory consolidation and archiving."""
        history = self.working.get()
        consolidated = self.archiver.consolidate_history(history, max_keep=40)
        self.working.history = consolidated

    # ── Tier 6: Experience Replay & Trajectory Learning ───────────────────

    def record_execution_experience(
        self,
        goal: str,
        success: bool,
        tool_sequence: List[str],
        failure_reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an execution trajectory to experience replay for autonomous learning."""
        traj = ExperienceTrajectory(
            goal_query=goal,
            success_status=success,
            step_count=len(tool_sequence),
            tool_sequence=tool_sequence,
            failure_reason=failure_reason,
            execution_context=context or {},
        )
        self.experience.record_trajectory(traj)

    def get_relevant_experiences(self, goal: str, limit: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve successful strategies and known failure pitfalls for similar goals."""
        return {
            "successes": self.experience.get_successful_patterns(goal, limit=limit),
            "failures": self.experience.get_similar_failures(goal, limit=limit),
        }

    def record_operational_lesson(
        self,
        tool_name: str,
        goal: str,
        success: bool,
        result_summary: str,
        failure_reason: Optional[str] = None,
    ) -> None:
        """Link a tool execution outcome directly to operational memory.

        Stores:
        - Trajectory in ExperienceReplayStore for pattern learning
        - Lesson in LessonStore if a verifiable failure occurred
        - Persistent memory note for significant successful verified operations
        """
        # 1. Always record trajectory
        self.record_execution_experience(
            goal=goal,
            success=success,
            tool_sequence=[tool_name],
            failure_reason=failure_reason,
        )

        # 2. Record lesson if this was a verified failure
        if not success and failure_reason:
            try:
                self.lessons.add_lesson(
                    topic=f"Tool:{tool_name} | Goal: {goal[:80]}",
                    correction=f"Failure: {failure_reason[:200]}",
                    source="tool_verifier",
                )
                logger.info(f"📚 Operational lesson recorded for failed tool: {tool_name}")
            except Exception as e:
                logger.debug("Lesson store add_lesson failed: %s", e)

        # 3. For significant successful verified operations, persist a memory note
        if success and len(result_summary) > 20:
            try:
                from datetime import datetime
                self.remember(
                    name=f"op_{tool_name}_{datetime.now().strftime('%Y%m%d')}",
                    content=f"Tool '{tool_name}' completed successfully for: {goal[:100]}. Result: {result_summary[:200]}",
                    description=f"Verified execution of {tool_name}",
                    mem_type="operational",
                    scope="user",
                    confidence=1.0,
                )
            except Exception:
                pass


_global_unified_memory: Optional[UnifiedMemoryManager] = None


def get_unified_memory() -> UnifiedMemoryManager:
    global _global_unified_memory
    if _global_unified_memory is None:
        _global_unified_memory = UnifiedMemoryManager()
    return _global_unified_memory
