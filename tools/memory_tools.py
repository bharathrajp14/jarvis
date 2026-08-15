# tools/memory_tools.py — Unified Production Memory Tools Suite
"""
Memory control tools plugin for BR JARVIS MK40.2.
Exposes complete memory lifecycle capabilities: save, search, get, update, delete, forget, stats, reindex.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from tools.registry import register_tool


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
            "confidence": {"type": "number", "description": "Confidence level (0.0 to 1.0, default: 1.0)"}
        },
        "required": ["name", "type", "description", "content"],
    }
)
def tool_memory_save(args: dict) -> str:
    from memory.persistent_store import MemoryEntry, save_memory, check_conflict
    scope = args.get("scope", "user")
    conf = float(args.get("confidence", 1.0))
    entry = MemoryEntry(
        name=args["name"],
        description=args["description"],
        type=args["type"],
        content=args["content"],
        created=datetime.now().strftime("%Y-%m-%d"),
        confidence=conf,
        scope=scope,
    )
    conflict = check_conflict(entry, scope=scope)
    save_memory(entry, scope=scope)
    msg = f"✅ Memory saved: '{entry.name}' [{entry.type}/{scope}] (confidence: {conf:.2f})"
    if conflict:
        msg += "\n⚠ Replaced conflicting older memory."
    return msg


@register_tool(
    name="memory_get",
    description="Retrieve a specific memory entry by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Memory entry name"},
            "scope": {"type": "string", "description": "Scope: 'user', 'project', or 'all'"}
        },
        "required": ["name"]
    }
)
def tool_memory_get(args: dict) -> str:
    from memory.persistent_store import load_index
    name = str(args.get("name", "")).strip().lower()
    scope = args.get("scope", "all")
    entries = load_index(scope=scope)
    for e in entries:
        if e.name.lower() == name or e.name.lower().replace(" ", "_") == name:
            return (
                f"### [{e.type.upper()} / {e.scope.upper()}] {e.name}\n"
                f"**Description:** {e.description}\n"
                f"**Created:** {e.created} | **Confidence:** {e.confidence:.2f}\n\n"
                f"{e.content}"
            )
    return f"Memory entry '{name}' not found."


@register_tool(
    name="memory_delete",
    description="Delete a persistent memory entry by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Memory name to delete"},
            "scope": {"type": "string", "description": "Scope: 'user' or 'project'"},
        },
        "required": ["name"],
    }
)
def tool_memory_delete(args: dict) -> str:
    from memory.persistent_store import delete_memory
    name = args["name"]
    scope = args.get("scope", "user")
    delete_memory(name, scope=scope)
    return f"🗑️ Memory deleted: '{name}' from [{scope}] scope."


@register_tool(
    name="memory_forget",
    description="Forget or invalidate memories matching a concept or query.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword or topic to forget"}
        },
        "required": ["query"]
    }
)
def tool_memory_forget(args: dict) -> str:
    from memory.persistent_store import search_memory, delete_memory
    query = args["query"]
    matches = search_memory(query)
    if not matches:
        return f"No memories found matching '{query}' to forget."
    deleted = []
    for m in matches:
        delete_memory(m.name, scope=m.scope)
        deleted.append(m.name)
    return f"🗑️ Successfully forgot {len(deleted)} memories: {', '.join(deleted)}"


@register_tool(
    name="memory_search",
    description="Search persistent memories by keyword with relevance, freshness, and confidence ranking.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword or phrase"},
            "max_results": {"type": "integer", "description": "Max results to return (default: 5)"},
        },
        "required": ["query"],
    }
)
def tool_memory_search(args: dict) -> str:
    from memory.unified_memory import get_unified_memory
    query = args.get("query", "")
    limit = args.get("max_results", 5)
    um = get_unified_memory()
    results = um.recall(query, limit=limit)
    
    if not results:
        return f"No memories found matching '{query}'."
        
    lines = [f"Found {len(results)} memory record(s) for '{query}':\n"]
    for r in results:
        lines.append(
            f"• [{r.get('source', 'memory').upper()}] **{r.get('name', 'Record')}** (Confidence: {r.get('confidence', 1.0):.2f})\n"
            f"  {r.get('content', '')[:300]}"
        )
    return "\n\n".join(lines)


@register_tool(
    name="memory_list",
    description="List all persistent memory entries across user and project scopes.",
    parameters={
        "type": "object",
        "properties": {
            "scope": {"type": "string", "description": "Scope filter: 'user', 'project', or 'all' (default: 'all')"},
        },
    }
)
def tool_memory_list(args: dict) -> str:
    from memory.persistent_store import load_entries
    scope_filter = args.get("scope", "all")
    scopes = ["user", "project"] if scope_filter == "all" else [scope_filter]
    
    all_entries = []
    for s in scopes:
        all_entries.extend(load_entries(s))
        
    if not all_entries:
        return "No memories stored."
        
    lines = [f"🧠 PERSISTENT MEMORY LEDGER ({len(all_entries)} total entries):"]
    for e in all_entries:
        tag = f"[{e.type.upper():<11} | {e.scope.upper():<7}]"
        lines.append(f" - {tag} {e.name:<30} | {e.description}")
    return "\n".join(lines)


@register_tool(
    name="memory_stats",
    description="Show memory diagnostics: total count by type, scope, storage size, and vector status.",
    parameters={"type": "object", "properties": {}}
)
def tool_memory_stats(args: dict) -> str:
    from memory.persistent_store import load_index, USER_MEMORY_DIR, get_project_memory_dir
    entries = load_index(scope="all")
    
    by_type = {}
    by_scope = {}
    total_chars = 0
    for e in entries:
        by_type[e.type] = by_type.get(e.type, 0) + 1
        by_scope[e.scope] = by_scope.get(e.scope, 0) + 1
        total_chars += len(e.content)
        
    lines = [
        "📊 JARVIS MEMORY OBSERVABILITY DIAGNOSTICS:",
        f" • Total Memory Records: {len(entries)}",
        f" • Total Content Volume: {total_chars:,} characters",
        f" • Scopes: " + ", ".join(f"{k}: {v}" for k, v in by_scope.items()),
        f" • Types: " + ", ".join(f"{k}: {v}" for k, v in by_type.items()),
        f" • User Memory Directory: {USER_MEMORY_DIR}",
        f" • Project Memory Directory: {get_project_memory_dir()}",
    ]
    return "\n".join(lines)


@register_tool(
    name="memory_reindex",
    description="Rebuild and synchronize memory indices across Markdown files, SQLite database, and vector embeddings.",
    parameters={"type": "object", "properties": {}}
)
def tool_memory_reindex(args: dict) -> str:
    from memory.persistent_store import reindex_all
    reindex_all()
    return "✅ Successfully reindexed and synchronized all persistent memories across Markdown, SQLite, and Vector stores."
