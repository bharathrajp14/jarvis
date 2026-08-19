# memory/consolidator.py
"""
Memory consolidator: extract long-term insights from completed sessions.

Called on /quit or programmatically after a session ends.
Uses a lightweight AI call to identify preferences, feedback, and project
decisions worth promoting to persistent memory.

Design principles:
  - Hard cap of 3 memories per session to avoid noise accumulation
  - Auto-extracted memories start at 0.8 confidence
  - Won't overwrite a higher-confidence existing memory
  - Skips short sessions (< MIN_MESSAGES_TO_CONSOLIDATE turns)

CRITICAL FIX (Phase 3):
  Previously wrote via persistent_store (memory.db) which was invisible to
  UnifiedMemoryManager.recall(). Now routes through UnifiedMemoryManager so
  session-extracted knowledge is immediately retrievable in the canonical store.
"""

from __future__ import annotations

import json
import re
import traceback

MIN_MESSAGES_TO_CONSOLIDATE = 8

_SYSTEM = """\
You are a memory consolidation assistant. Analyze the conversation below and extract
insights that are worth storing as persistent memories for future sessions.

Focus ONLY on:
1. New user preferences or working-style corrections revealed in this session
2. Project decisions or facts made explicit (NOT derivable from code/git)
3. Behavioral feedback given to the AI (what to do or avoid, and why)

Return a JSON object with key "memories" containing a list of objects, each with:
  "name":        short slug, e.g. "user_prefers_concise_responses"
  "type":        "user" | "feedback" | "preference" | "project" | "lesson"
  "description": one-line description (used for search relevance)
  "content":     memory body
  "confidence":  float 0.0-1.0 (use ~0.8 for inferred, ~0.9 for clearly stated)

Return {"memories": []} if nothing new or worth saving.

Do NOT extract:
- Code patterns, architecture, file paths -- derivable from the codebase
- Git history or debugging fixes -- already in commits
- Ephemeral task state or tool results

Keep to AT MOST 3 memories. Quality over quantity."""


def consolidate_session(messages: list, router=None) -> list[str]:
    """Analyze a session's messages and extract memories worth keeping.

    Args:
        messages: the conversation message list
        router:   AgentRouter instance (to call an LLM)

    Returns:
        List of memory_ids that were saved. Empty list on skip or error.
    """
    if len(messages) < MIN_MESSAGES_TO_CONSOLIDATE:
        return []

    if router is None:
        return []

    try:
        from brjarvis.memory.domain import CanonicalMemory, MemoryType, SourceType, redact_secrets
        from brjarvis.memory.unified_memory import get_unified_memory

        # Build condensed transcript from the last 40 messages
        recent = messages[-40:]
        parts: list[str] = []
        for m in recent:
            role = m.get("role", "")
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                prefix = "User" if role == "user" else "Assistant"
                snippet = content[:600].replace("\n", " ")
                parts.append(f"{prefix}: {snippet}")

        if not parts:
            return []

        transcript = "\n".join(parts)

        consolidation_messages = [{"role": "user", "content": f"Conversation:\n\n{transcript}"}]

        try:
            result_text = router.run(
                router.default,
                consolidation_messages,
                _SYSTEM,
            )
        except Exception:
            return []

        if not result_text:
            return []

        # Parse JSON (strip markdown code blocks if present)
        clean = re.sub(r"```(?:json)?", "", result_text).strip().rstrip("`").strip()
        parsed = json.loads(clean)
        memories_data = parsed.get("memories", [])
        if not isinstance(memories_data, list):
            return []

        _type_map = {
            "user": MemoryType.USER_PROFILE,
            "feedback": MemoryType.OBSERVATION,
            "preference": MemoryType.PREFERENCE,
            "project": MemoryType.PROJECT_STATE,
            "lesson": MemoryType.LESSON,
            "semantic": MemoryType.SEMANTIC,
        }

        mem_manager = get_unified_memory()
        saved: list[str] = []

        for m in memories_data[:3]:  # hard cap: max 3 per session
            required = ("name", "type", "description", "content")
            if not all(k in m for k in required):
                continue

            confidence = float(m.get("confidence", 0.8))
            mem_type = _type_map.get(str(m.get("type", "user")).lower(), MemoryType.SEMANTIC)

            # Apply secret redaction before persistence
            content_text = redact_secrets(str(m["content"]))

            canonical = CanonicalMemory(
                entity=str(m["name"]),
                attribute=str(m.get("type", "user")),
                content=content_text,
                memory_type=mem_type,
                scope="user",
                confidence=confidence,
                importance=0.65,
                source_type=SourceType.STRONG_INFERENCE,
            )

            try:
                result = mem_manager.remember(canonical)
                if result:
                    saved.append(result.memory_id)
            except Exception:
                traceback.print_exc()
                continue

        return saved

    except Exception:
        traceback.print_exc()
        return []
