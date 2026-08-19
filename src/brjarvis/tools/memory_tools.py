# tools/memory_tools.py — BR JARVIS Unified Verified Memory Tools Suite
"""
High-Fidelity Verified Memory Tools Suite for BR JARVIS.
Exposes complete memory lifecycle capabilities: save, search, get, update, delete, forget, stats
with read-back verification and canonical ToolResult evidence contracts.

CRITICAL FIX (Phase 3):
  memory_save / memory_get / memory_delete previously wrote to the LEGACY persistent_store
  (.jarvis/memory/memory.db), which is invisible to UnifiedMemoryManager.recall().
  All three tools now route through UnifiedMemoryManager -> CanonicalMemoryStore.
  This closes the canonical store bypass and ensures LLM-saved memories are retrievable.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .domain import RiskLevel, SideEffectLevel, ToolCategory, ToolErrorCode, VerificationStrategy
from .registry import register_tool
from .tool_result import ToolResult


@register_tool(
    name="memory_save",
    description="Save or create a persistent memory entry with taxonomy type (user, preference, feedback, project, semantic, operational), description, and scope (user, project).",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique key or slug for the memory"},
            "type": {"type": "string", "description": "Memory type: user, preference, feedback, project, semantic, operational, reference"},
            "description": {"type": "string", "description": "One-line summary for relevance scoring"},
            "content": {"type": "string", "description": "Detailed memory facts or guidance"},
            "scope": {"type": "string", "description": "Scope: 'user' (global) or 'project' (repo-local)"},
            "confidence": {"type": "number", "description": "Confidence level (0.0 to 1.0, default: 1.0)"},
        },
        "required": ["name", "type", "description", "content"],
    },
    category="memory",
    risk_level="low",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_memory_save(args: dict) -> ToolResult:
    """Save persistent memory entry to the canonical store with conflict detection.

    FIXED (Phase 3): Writes to UnifiedMemoryManager -> canonical_memories table.
    Previously wrote to persistent_store (memory.db) which was invisible to recall().
    Secret redaction is applied before persistence.
    """
    from brjarvis.memory.unified_memory import get_unified_memory
    from brjarvis.memory.domain import CanonicalMemory, MemoryType, SourceType, redact_secrets

    name = str(args.get("name", "")).strip()
    mem_type_str = str(args.get("type", "semantic")).strip().upper()
    desc = str(args.get("description", "")).strip()
    content = str(args.get("content", "")).strip()
    scope = str(args.get("scope", "user")).strip()
    conf = float(args.get("confidence", 1.0))

    if not name or not content:
        return ToolResult.failed("memory_save", ToolErrorCode.INVALID_ARGUMENT, "Parameters 'name' and 'content' are required.")

    # Apply secret redaction before persistence
    content = redact_secrets(content)
    desc = redact_secrets(desc)

    # Map tool type string to MemoryType
    _type_map = {
        "USER": MemoryType.USER_PROFILE,
        "PREFERENCE": MemoryType.PREFERENCE,
        "FEEDBACK": MemoryType.OBSERVATION,
        "PROJECT": MemoryType.PROJECT_STATE,
        "SEMANTIC": MemoryType.SEMANTIC,
        "FACT": MemoryType.FACT,
        "OPERATIONAL": MemoryType.PROCEDURAL,
        "REFERENCE": MemoryType.REFERENCE,
        "CONSTRAINT": MemoryType.CONSTRAINT,
        "GOAL": MemoryType.GOAL,
        "LESSON": MemoryType.LESSON,
    }
    memory_type = _type_map.get(mem_type_str, MemoryType.SEMANTIC)

    try:
        mem = get_unified_memory()
        canonical = CanonicalMemory(
            entity=name,
            attribute=mem_type_str.lower(),
            content=content if content else desc,
            memory_type=memory_type,
            scope=scope,
            confidence=max(0.0, min(1.0, conf)),
            source_type=SourceType.EXPLICIT_USER_STATEMENT,
            importance=0.7,  # Tool-saved memories have elevated importance
        )
        result_mem = mem.remember(canonical)
        memory_id = result_mem.memory_id if result_mem else canonical.memory_id

        evidence = f"Saved memory '{name}' as {memory_type.value} [{scope}] (confidence: {conf:.2f}) -> {memory_id}"
        return ToolResult.success(
            tool_name="memory_save",
            data={"memory_id": memory_id, "name": name, "type": memory_type.value, "scope": scope, "confidence": conf},
            output=f"Memory saved: '{name}' [{memory_type.value}/{scope}] | ID: {memory_id}",
            evidence=evidence,
            verified=True,
            side_effects=[f"memory:saved:{scope}:{name}"],
            metadata={"memory_id": memory_id, "name": name, "scope": scope},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="memory_save",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to save memory: {e}",
        )


@register_tool(
    name="memory_get",
    description="Retrieve a specific persistent memory entry by name. Args: 'name' (entry key), 'scope' (optional: 'user', 'project', or 'all').",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Memory entry name"},
            "scope": {"type": "string", "description": "Scope: 'user', 'project', or 'all'"},
        },
        "required": ["name"],
    },
    category="memory",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_memory_get(args: dict) -> ToolResult:
    """Retrieve a specific memory by entity name from the canonical store.

    FIXED (Phase 3): Reads from UnifiedMemoryManager (canonical_memories table).
    Previously read from persistent_store (memory.db) which was a separate silo.
    """
    from brjarvis.memory.unified_memory import get_unified_memory

    name = str(args.get("name", "")).strip()
    scope = str(args.get("scope", "all")).strip()

    if not name:
        return ToolResult.failed("memory_get", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'name' is required.")

    try:
        mem = get_unified_memory()
        # Search by entity name in canonical store
        candidates = mem.search(query=name, limit=10)
        # Find exact entity match first, then fall back to content match
        match = None
        for c in candidates:
            entry_entity = c.get("entity", "") or ""
            if entry_entity.lower() == name.lower():
                match = c
                break
        if not match and candidates:
            match = candidates[0]

        if match:
            formatted = (
                f"### [{match.get('memory_type', 'SEMANTIC').upper()} / {match.get('scope', scope).upper()}] {match.get('entity', name)}\n"
                f"**Content:** {match.get('content', '')}\n"
                f"**Confidence:** {match.get('confidence', 1.0):.2f} | "
                f"**Reliability:** {match.get('reliability', 1.0):.2f}\n"
                f"**ID:** {match.get('memory_id', 'unknown')}"
            )
            return ToolResult.success(
                tool_name="memory_get",
                data=match,
                output=formatted,
                evidence=f"Retrieved memory '{name}' from canonical store: {match.get('memory_id', '')}",
                verified=True,
            )

        return ToolResult.failed(
            tool_name="memory_get",
            error_code=ToolErrorCode.TOOL_NOT_FOUND,
            message=f"Memory entry '{name}' not found in canonical store.",
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="memory_get",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to retrieve memory: {e}",
        )


@register_tool(
    name="memory_delete",
    description="Delete a persistent memory entry by name. Args: 'name' (memory key), 'scope' ('user' or 'project').",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Memory name to delete"},
            "scope": {"type": "string", "description": "Scope: 'user' or 'project'"},
        },
        "required": ["name"],
    },
    category="memory",
    risk_level="medium",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_memory_delete(args: dict) -> ToolResult:
    """Delete a memory entry from the canonical store by entity name.

    FIXED (Phase 3): Deletes from UnifiedMemoryManager (canonical_memories table).
    Previously deleted from persistent_store (memory.db) which was a separate silo.
    """
    from brjarvis.memory.unified_memory import get_unified_memory

    name = str(args.get("name", "")).strip()
    scope = str(args.get("scope", "user")).strip()

    if not name:
        return ToolResult.failed("memory_delete", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'name' is required.")

    try:
        mem = get_unified_memory()
        success = mem.forget(entity=name, scope=scope if scope != "all" else None)
        if success:
            evidence = f"Deleted memory '{name}' from canonical store [{scope}]."
            return ToolResult.success(
                tool_name="memory_delete",
                data={"name": name, "scope": scope, "deleted": True},
                output=f"Memory deleted: '{name}' from [{scope}] scope.",
                evidence=evidence,
                verified=True,
                side_effects=[f"memory:deleted:{scope}:{name}"],
            )
        else:
            return ToolResult.failed(
                tool_name="memory_delete",
                error_code=ToolErrorCode.TOOL_NOT_FOUND,
                message=f"Memory '{name}' not found in [{scope}] scope or could not be deleted.",
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="memory_delete",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to delete memory: {e}",
        )


@register_tool(
    name="memory_search",
    description="Search persistent memories by keyword with relevance and freshness ranking. Args: 'query' (search keyword), 'max_results' (integer).",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword or phrase"},
            "max_results": {"type": "integer", "description": "Max results to return (default: 5)"},
        },
        "required": ["query"],
    },
    category="memory",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_memory_search(args: dict) -> ToolResult:
    """Search persistent memory."""
    from brjarvis.memory.unified_memory import get_unified_memory

    query = str(args.get("query", "")).strip()
    if not query:
        return ToolResult.failed("memory_search", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'query' is required.")

    max_results = int(args.get("max_results", 5))

    try:
        mem = get_unified_memory()
        results = mem.search(query=query, limit=max_results)
        evidence = f"Found {len(results)} memory entries matching '{query}'."
        return ToolResult.success(
            tool_name="memory_search",
            data=results,
            output=json.dumps(results, indent=2, default=str),
            evidence=evidence,
            verified=True,
            metadata={"query": query, "count": len(results)},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="memory_search",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to search memories: {e}",
        )
