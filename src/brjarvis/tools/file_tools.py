# tools/file_tools.py — JARVIS MK37 File Tools Plugin
"""
File tools plugin for JARVIS MK37. Contains file_read, file_write, and file_list.
"""
from __future__ import annotations

from pathlib import Path
from brjarvis.core.paths import paths
from .registry import register_tool
from .files import FileManager

# Initialize the file manager relative to the project workspace directory
WORKSPACE_DIR = paths.WORKSPACE_ROOT
_files = FileManager(workspace=str(WORKSPACE_DIR))


@register_tool(
    name="file_read",
    description="Read a file from the workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path within the workspace"},
        },
        "required": ["path"],
    }
)
def tool_file_read(args: dict) -> str:
    path = args["path"]
    return _files.read(path)


@register_tool(
    name="file_write",
    description="Write content to a file in the workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path within the workspace"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    }
)
def tool_file_write(args: dict) -> str:
    path = args["path"]
    content = args["content"]
    _files.write(path, content)
    return f"File written: {path}"


@register_tool(
    name="file_list",
    description="List files in a workspace directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative directory path (default: root)"},
        },
    }
)
def tool_file_list(args: dict) -> str:
    path = args.get("path", ".")
    items = _files.list_dir(path)
    return "\n".join(items)
