# tools/export_tools.py — JARVIS MK37 & MK40 Export Tools Plugin
"""
Registers chat log, working memory, and verified sandbox artifact export tools in the tool registry.
"""
from __future__ import annotations

import json
from pathlib import Path
from .registry import register_tool
from brjarvis.agent.artifacts import get_artifact_manager


@register_tool(
    name="export_chat",
    description="Export the current conversation/chat history to a file. Formats: pdf, md (Markdown), html, txt.",
    parameters={
        "type": "object",
        "properties": {
            "format": {"type": "string", "description": "Output file format: 'pdf', 'md', 'html', 'txt' (default: pdf)"},
            "max_turns": {"type": "integer", "description": "Maximum conversation turns to export (default: 100)"},
        },
        "required": ["format"],
    }
)
def tool_export_chat(args: dict) -> str:
    from brjarvis.actions.chat_export import export_chat
    result = export_chat(
        format=args["format"],
        max_turns=args.get("max_turns", 100),
    )
    return json.dumps(result, indent=2, default=str)


@register_tool(
    name="artifact_export",
    description="Export a user-facing artifact generated inside the sandbox to the verified safe host workspace directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Source path of the artifact inside sandbox or workspace"},
            "filename": {"type": "string", "description": "Optional custom filename on host"},
            "task_id": {"type": "string", "description": "Optional task ID"}
        },
        "required": ["path"]
    }
)
def tool_artifact_export(args: dict) -> str:
    mgr = get_artifact_manager()
    src_path = args.get("path") or args.get("sandbox_path") or ""
    custom_name = args.get("filename")
    task_id = args.get("task_id", "default")

    rec = mgr.export_sandbox_artifact(src_path, task_id=task_id, custom_filename=custom_name)
    if not rec.exported:
        return json.dumps({
            "status": "error",
            "message": f"Artifact created, but could not export it to the user workspace: {rec.error}",
            "record": rec.to_dict()
        }, indent=2)

    return json.dumps({
        "status": "success",
        "message": f"⚡ Exported artifact '{rec.filename}' to host workspace: {rec.host_path}",
        "record": rec.to_dict()
    }, indent=2)


@register_tool(
    name="artifact_list",
    description="List all verified exported host artifacts and their integrity hashes.",
    parameters={}
)
def tool_artifact_list(args: dict) -> str:
    mgr = get_artifact_manager()
    records = mgr.list_artifacts()
    return json.dumps([r.to_dict() for r in records], indent=2)
