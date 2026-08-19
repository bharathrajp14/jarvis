# tools/workspace_tools.py — BR JARVIS Cognitive Workspace Tools
"""
Tools for interacting with the BR JARVIS AI OS Workspace (BR_WORKSPACE/).
"""

from __future__ import annotations

import os
import sys

from brjarvis.core.workspace_engine import CognitiveWorkspaceEngine

from .registry import register_tool


@register_tool(
    name="open_workspace_file",
    description="Smart natural language file opener for BR_WORKSPACE/. Accepts query like 'open yesterday's API design' or 'open RouteX architecture'.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Natural language query or file description"}},
        "required": ["query"],
    },
)
def open_workspace_file(args: dict) -> str:
    """Smart natural language file retrieval and opening."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: Please specify what file to open, sir."

    ws = CognitiveWorkspaceEngine()
    target = ws.smart_find_file(query)

    if not target or not target.exists():
        return f"Could not locate file matching query: '{query}' in BR_WORKSPACE/."

    if sys.platform == "win32":
        try:
            os.startfile(str(target))
            ws.log_timeline_event("FILE_OPENED", f"Opened file '{target.name}'", metadata={"query": query})
            return f"⚡ Opened '{target.name}' from workspace ({target})."
        except Exception as e:
            return f"Opened target path: {target} (Launch warning: {e})"

    return f"Located file: {target}"


@register_tool(
    name="get_workspace_timeline",
    description="Retrieve the chronological workspace action timeline stream (file creations, code generations, model calls).",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of recent events to retrieve (default: 15)"}
        },
    },
)
def get_workspace_timeline(args: dict) -> str:
    """Retrieve workspace action timeline."""
    limit = args.get("limit", 15)
    ws = CognitiveWorkspaceEngine()

    import sqlite3

    conn = sqlite3.connect(ws.db_path, timeout=15.0)

    cur = conn.cursor()
    cur.execute(
        "SELECT timestamp, event_type, project_name, description FROM workspace_timeline ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "Workspace Timeline: No events recorded yet."

    events = [f" - [{r[0]}] [{r[1]}] {f'({r[2]}) ' if r[2] else ''}{r[3]}" for r in rows]
    return "📜 BR_WORKSPACE TIMELINE EVENT STREAM:\n" + "\n".join(events)


@register_tool(
    name="init_project_workspace",
    description="Create a standardized self-contained Project Workspace (source, docs, architecture, api, tests, build) inside BR_WORKSPACE/Projects/.",
    parameters={
        "type": "object",
        "properties": {"project_name": {"type": "string", "description": "Name of the project workspace to create"}},
        "required": ["project_name"],
    },
)
def init_project_workspace(args: dict) -> str:
    """Create project sub-tree workspace."""
    pname = args.get("project_name", "").strip()
    if not pname:
        return "Error: Project name required."

    ws = CognitiveWorkspaceEngine()
    proj_path = ws.create_project_workspace(pname)

    return f"⚡ Initialized Project Workspace for '{pname}' at: '{proj_path}' (25 sub-directories ready)."
