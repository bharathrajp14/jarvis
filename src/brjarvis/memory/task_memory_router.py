# memory/task_memory_router.py — BR JARVIS Adaptive Task Memory Router
"""
Lightweight, zero-latency task memory classifier.

Before every orchestrator chat() call, this router scores the incoming task
against available memory context and returns one of three MemoryMode values:

  FRESH          — Task is independent. Start clean (no history injected).
  LOAD_RELEVANT  — Task references prior context. Inject only matching slices.
  LOAD_FULL      — Complex continuation. Inject full session history.

Decision cascade (all fast, in-process):
  1. Heuristic keyword check     — O(1), no I/O
  2. Token budget check          — O(1), no I/O
  3. Semantic vector search      — O(log N), ChromaDB lookup
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from enum import Enum
from typing import List, Optional, Dict, Any

logger = logging.getLogger("JARVIS.TaskMemoryRouter")

# ── Memory Mode Enum ──────────────────────────────────────────────────────────

class MemoryMode(Enum):
    """Describes how much memory context to inject for the current task."""
    FRESH = "fresh"                # No memory injected — clean start
    LOAD_RELEVANT = "relevant"    # Only semantically matched memory slices
    LOAD_FULL = "full"            # Full working memory history injected


# ── Heuristic Patterns ────────────────────────────────────────────────────────

# Phrases strongly indicating the user is referencing prior conversation/work
_CONTINUATION_PATTERNS = re.compile(
    r"\b("
    r"earlier|before|previously|last time|we were|we discussed|you said|you told|"
    r"as I mentioned|from before|continue|pick up|resume|remember when|"
    r"that project|that file|that code|the one|go back|same as|like before|"
    r"what we|where we|our conversation|our session|you were|it was|"
    r"you just|you already|i asked|i said|i told you|that thing|that task"
    r")\b",
    re.IGNORECASE,
)

# Phrases strongly indicating a completely new, independent task
_FRESH_PATTERNS = re.compile(
    r"^(hey jarvis[,.]?\s*)?"
    r"(what is|what are|what's|what time|what day|what date|what year|"
    r"who is|who are|where is|where are|"
    r"define|explain|how do|how does|how many|how much|"
    r"calculate|compute|convert|translate|"
    r"tell me|show me|give me|"
    r"open|launch|close|start|run|"
    r"search|find|look up|google|"
    r"play|stop|pause|resume|"
    r"check|get|fetch|list|"
    r"set|create new|make a new|start fresh|write a|make a|"
    r"new task|new request|forget|ignore previous|"
    r"weather|news|time|date|today|tomorrow|temperature)"
    r"\b",
    re.IGNORECASE,
)

# Temporal markers that suggest session continuation
_TEMPORAL_MARKERS = re.compile(
    r"\b(earlier today|just now|a moment ago|few minutes ago|"
    r"in our chat|in this session|in this conversation)\b",
    re.IGNORECASE,
)

# ── Result Cache ──────────────────────────────────────────────────────────────

_CLASSIFICATION_CACHE: Dict[str, tuple[MemoryMode, float]] = {}
_CACHE_TTL_SECONDS = 30.0   # Classification valid for 30 seconds


def _cache_key(task: str) -> str:
    return hashlib.md5(task.strip().lower().encode()).hexdigest()[:16]


def _get_cached(task: str) -> Optional[MemoryMode]:
    key = _cache_key(task)
    if key in _CLASSIFICATION_CACHE:
        mode, ts = _CLASSIFICATION_CACHE[key]
        if (time.monotonic() - ts) < _CACHE_TTL_SECONDS:
            return mode
        del _CLASSIFICATION_CACHE[key]
    return None


def _set_cached(task: str, mode: MemoryMode) -> None:
    key = _cache_key(task)
    _CLASSIFICATION_CACHE[key] = (mode, time.monotonic())


# ── Main Classifier ───────────────────────────────────────────────────────────

class TaskMemoryRouter:
    """
    3-tier memory relevance classifier for BR JARVIS.

    Usage:
        router = TaskMemoryRouter()
        mode = router.classify("continue the analysis from earlier")
        # Returns MemoryMode.LOAD_RELEVANT

        slices = router.get_relevant_slices("continue the analysis from earlier", limit=4)
        # Returns list of memory dicts to inject
    """

    def __init__(
        self,
        token_budget_pct_threshold: float = 0.60,
        semantic_score_threshold: float = 0.72,
    ):
        """
        Args:
            token_budget_pct_threshold: If working memory exceeds this fraction
                of the max context budget, force FRESH to avoid overflow.
            semantic_score_threshold: Minimum cosine similarity to consider a
                memory slice relevant to the current task (0.0-1.0).
        """
        self.token_budget_pct_threshold = token_budget_pct_threshold
        self.semantic_score_threshold = semantic_score_threshold

    # ── Tier 1: Zero-Token Heuristic ─────────────────────────────────────────

    def _heuristic_classify(self, task: str) -> Optional[MemoryMode]:
        """
        Fast keyword-level classification. Returns a MemoryMode if confident,
        or None if uncertain (hand off to deeper tiers).
        """
        # Explicit continuation signal → always load relevant context
        if _CONTINUATION_PATTERNS.search(task):
            logger.debug("Heuristic: CONTINUATION pattern matched → LOAD_RELEVANT")
            return MemoryMode.LOAD_RELEVANT

        # Temporal session marker → likely a continuation
        if _TEMPORAL_MARKERS.search(task):
            logger.debug("Heuristic: TEMPORAL marker matched → LOAD_RELEVANT")
            return MemoryMode.LOAD_RELEVANT

        # Clear independent command → fresh start
        if _FRESH_PATTERNS.match(task.strip()):
            logger.debug("Heuristic: FRESH pattern matched → FRESH")
            return MemoryMode.FRESH

        # Very short single-word commands → always fresh
        if len(task.split()) <= 2:
            logger.debug("Heuristic: Short command → FRESH")
            return MemoryMode.FRESH

        return None  # Uncertain — proceed to deeper tiers

    # ── Tier 2: Token Budget Guard ────────────────────────────────────────────

    def _check_token_budget(self, working_memory_tokens: int, max_tokens: int) -> Optional[MemoryMode]:
        """
        If working memory is already near the context ceiling, force FRESH
        to avoid overflowing the LLM's context window.
        """
        if max_tokens <= 0:
            return None
        pct = working_memory_tokens / max_tokens
        if pct >= self.token_budget_pct_threshold:
            logger.debug(
                "Token budget: %.1f%% used (threshold %.1f%%) → forcing FRESH",
                pct * 100, self.token_budget_pct_threshold * 100
            )
            return MemoryMode.FRESH
        return None

    # ── Tier 3: Semantic Vector Search ───────────────────────────────────────

    def _semantic_classify(self, task: str) -> MemoryMode:
        """
        Performs a lightweight semantic search against the vector memory store.
        If any stored memory scores above the similarity threshold, the task is
        considered a continuation (LOAD_RELEVANT). Otherwise FRESH.
        """
        try:
            from memory.vector_store import VectorMemory
            vm = VectorMemory()
            results = vm.recall(task, n=1)
            if results:
                # VectorMemory.recall returns text strings; check if non-trivial
                top_result = results[0]
                if isinstance(top_result, str) and len(top_result.strip()) > 20:
                    logger.debug("Semantic search: relevant memory found → LOAD_RELEVANT")
                    return MemoryMode.LOAD_RELEVANT
        except Exception as e:
            logger.debug("Semantic search unavailable: %s", e)

        logger.debug("Semantic search: no relevant memory → FRESH")
        return MemoryMode.FRESH

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(
        self,
        task: str,
        working_memory_tokens: int = 0,
        max_context_tokens: int = 100_000,
        max_tokens: int | None = None,
        **kwargs,
    ) -> MemoryMode:
        if max_tokens is not None:
            max_context_tokens = max_tokens

        """
        Classify a task and return the appropriate MemoryMode.

        Args:
            task: The raw user task/query string.
            working_memory_tokens: Current token count of working memory.
            max_context_tokens: Maximum context window size for the current backend.

        Returns:
            MemoryMode (FRESH | LOAD_RELEVANT | LOAD_FULL)
        """
        if not task or not task.strip():
            return MemoryMode.FRESH

        # Check classification cache first
        cached = _get_cached(task)
        if cached is not None:
            logger.debug("Cache hit: %s → %s", task[:40], cached.value)
            return cached

        # ── Tier 0: Empty working memory → skip semantic search entirely ───────
        # Prevents stale ChromaDB vectors from producing false LOAD_RELEVANT.
        if working_memory_tokens == 0:
            result = self._heuristic_classify(task)
            _set_cached(task, result or MemoryMode.FRESH)
            return result if result is not None else MemoryMode.FRESH

        # Tier 1: Fast heuristic
        result = self._heuristic_classify(task)

        # Tier 2: Token budget guard
        if result is None:
            result = self._check_token_budget(working_memory_tokens, max_context_tokens)

        # Tier 3: Semantic vector search
        if result is None:
            result = self._semantic_classify(task)

        logger.info(
            "TaskMemoryRouter: '%s...' → %s",
            task[:50].replace("\n", " "),
            result.value.upper()
        )
        _set_cached(task, result)
        return result

    def get_relevant_slices(
        self,
        task: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        When classify() returns LOAD_RELEVANT, call this to retrieve
        only the memory slices that are actually relevant to the task.

        Returns list of memory dicts: {source, name, content, confidence}
        """
        slices: List[Dict[str, Any]] = []

        try:
            from memory.unified_memory import get_unified_memory
            mem = get_unified_memory()
            hits = mem.recall(task, limit=limit)
            slices.extend(hits)
        except Exception as e:
            logger.warning("get_relevant_slices failed: %s", e)

        return slices

    def format_memory_injection(
        self,
        slices: List[Dict[str, Any]],
        mode: MemoryMode,
    ) -> str:
        """
        Format memory slices into a compact system-prompt injection block.
        Returns an empty string when mode is FRESH.
        """
        if mode == MemoryMode.FRESH or not slices:
            return ""

        lines = ["### 📋 Relevant Memory Context (auto-injected):"]
        for i, s in enumerate(slices, 1):
            source = s.get("source", "memory")
            name = s.get("name", f"Memory {i}")
            content = str(s.get("content", "")).strip()
            if content:
                # Truncate very long memory items to avoid token bloat
                if len(content) > 400:
                    content = content[:400] + "…"
                lines.append(f"[{i}] ({source}) {name}: {content}")

        if len(lines) == 1:
            return ""  # No content to inject

        lines.append("### (End of Memory Context)\n")
        return "\n".join(lines)


# ── Module-Level Singleton ────────────────────────────────────────────────────

_router_singleton: Optional[TaskMemoryRouter] = None


def get_task_memory_router() -> TaskMemoryRouter:
    """Return or create the global TaskMemoryRouter singleton."""
    global _router_singleton
    if _router_singleton is None:
        _router_singleton = TaskMemoryRouter()
    return _router_singleton
