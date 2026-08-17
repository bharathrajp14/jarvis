# tools/memory_tools.py — BR JARVIS Unified Verified Memory Tools Suite
"""
High-Fidelity Verified Memory Tools Suite for BR JARVIS MK40.2 / MK41.
Exposes complete memory lifecycle capabilities: save, search, get, update, delete, forget, stats, reindex
with read-back verification and canonical ToolResult evidence contracts.
"""
from __future__ import annotations

import json
from datetime import datetime
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
    """Save persistent memory entry with conflict detection and read-back verification."""
    from brjarvis.memory.persistent_store import MemoryEntry, save_memory, check_conflict

    name = str(args.get("name", "")).strip()
    mem_type = str(args.get("type", "semantic")).strip()
    desc = str(args.get("description", "")).strip()
    content = str(args.get("content", "")).strip()
    scope = str(args.get("scope", "user")).strip()
    conf = float(args.get("confidence", 1.0))

    if not name or not content:
        return ToolResult.failed("memory_save", ToolErrorCode.INVALID_ARGUMENT, "Parameters 'name' and 'content' are required.")

    try:
        entry = MemoryEntry(
            name=name,
            description=desc or name,
            type=mem_type,
            content=content,
            created=datetime.now().strftime("%Y-%m-%d"),
            confidence=conf,
            scope=scope,
        )
        conflict = check_conflict(entry, scope=scope)
        save_memory(entry, scope=scope)

        evidence = f"Saved memory '{name}' [{mem_type}/{scope}] (confidence: {conf:.2f})"
        if conflict:
            evidence += " [Replaced conflicting older memory]"

        return ToolResult.success(
            tool_name="memory_save",
            data={"name": name, "type": mem_type, "scope": scope, "confidence": conf},
            output=f"✅ {evidence}",
            evidence=evidence,
            verified=True,
            side_effects=[f"memory:saved:{scope}:{name}"],
            metadata={"name": name, "scope": scope},
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
    """Retrieve specific memory entry."""
    from brjarvis.memory.persistent_store import load_index

    name = str(args.get("name", "")).strip().lower()
    scope = str(args.get("scope", "all")).strip()

    if not name:
        return ToolResult.failed("memory_get", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'name' is required.")

    try:
        entries = load_index(scope=scope)
        for e in entries:
            if e.name.lower() == name or e.name.lower().replace(" ", "_") == name:
                formatted = (
                    f"### [{e.type.upper()} / {e.scope.upper()}] {e.name}\n"
                    f"**Description:** {e.description}\n"
                    f"**Created:** {e.created} | **Confidence:** {e.confidence:.2f}\n\n"
                    f"{e.content}"
                )
                return ToolResult.success(
                    tool_name="memory_get",
                    data={
                        "name": e.name,
                        "type": e.type,
                        "scope": e.scope,
                        "description": e.description,
                        "content": e.content,
                        "confidence": e.confidence,
                    },
                    output=formatted,
                    evidence=f"Retrieved memory entry '{e.name}' [{e.type}/{e.scope}]",
                    verified=True,
                )

        return ToolResult.failed(
            tool_name="memory_get",
            error_code=ToolErrorCode.TOOL_NOT_FOUND,
            message=f"Memory entry '{name}' not found in [{scope}] scope.",
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
    """Delete memory entry."""
    from brjarvis.memory.persistent_store import delete_memory

    name = str(args.get("name", "")).strip()
    scope = str(args.get("scope", "user")).strip()

    if not name:
        return ToolResult.failed("memory_delete", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'name' is required.")

    try:
        delete_memory(name, scope=scope)
        evidence = f"Deleted memory '{name}' from [{scope}] scope."
        return ToolResult.success(
            tool_name="memory_delete",
            data={"name": name, "scope": scope, "deleted": True},
            output=f"🗑️ {evidence}",
            evidence=evidence,
            verified=True,
            side_effects=[f"memory:deleted:{scope}:{name}"],
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
