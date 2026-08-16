# tools/file_tools.py — BR JARVIS High-Fidelity Verified Filesystem Suite
"""
High-Fidelity Verified Filesystem Tools Suite for BR JARVIS MK40.2 / MK41.
Guarantees atomic file writes, SHA-256 content hashing, workspace boundary enforcement,
soft-delete (trash) safeguards, and canonical ToolResult evidence contracts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths
from .domain import RiskLevel, SideEffectLevel, ToolCategory, ToolErrorCode, VerificationStrategy
from .files import FileManager
from .registry import register_tool
from .tool_result import ToolResult

_files = FileManager(workspace=paths.WORKSPACE_ROOT)


@register_tool(
    name="file_read",
    description="Read file contents from the workspace. Args: 'path' (relative path within workspace), 'max_bytes' (optional byte limit).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path within workspace"},
            "max_bytes": {"type": "integer", "description": "Maximum bytes to read (default: 10,000,000)"},
        },
        "required": ["path"],
    },
    category="filesystem",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
    verification_strategy="FILE_EXISTS",
)
def tool_file_read(args: dict) -> ToolResult:
    """Read file contents with verification metadata."""
    path = str(args.get("path", "")).strip()
    if not path:
        return ToolResult.failed("file_read", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'path' is required.")

    max_bytes = int(args.get("max_bytes", 10_000_000))

    try:
        read_meta = _files.read(path, max_bytes=max_bytes)
        evidence = (
            f"Read {read_meta['size_bytes']:,} bytes ({read_meta['line_count']} lines) from '{path}' "
            f"[SHA256: {read_meta['sha256'][:10]}...]"
        )
        return ToolResult.success(
            tool_name="file_read",
            data=read_meta["content"],
            output=read_meta["content"],
            evidence=evidence,
            verified=True,
            metadata=read_meta,
        )
    except FileNotFoundError:
        return ToolResult.failed(
            tool_name="file_read",
            error_code=ToolErrorCode.TOOL_NOT_FOUND,
            message=f"File not found on disk: '{path}'",
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="file_read",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error reading file '{path}': {e}",
        )


@register_tool(
    name="file_write",
    description="Write content atomically to a file in the workspace with SHA-256 verification. Args: 'path' (relative path), 'content' (text content to write).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path within workspace"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
    category="filesystem",
    risk_level="medium",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="FILE_CONTENT",
)
def tool_file_write(args: dict) -> ToolResult:
    """Perform atomic file write with hash and size verification."""
    path = str(args.get("path", "")).strip()
    content = args.get("content", "")

    if not path:
        return ToolResult.failed("file_write", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'path' is required.")

    try:
        write_meta = _files.write_atomic(path, content)
        evidence = (
            f"Atomically wrote {write_meta['size_bytes']:,} bytes ({write_meta['line_count']} lines) "
            f"to '{write_meta['relative_path']}' [SHA256: {write_meta['sha256'][:10]}...]"
        )
        return ToolResult.success(
            tool_name="file_write",
            data=write_meta,
            output=evidence,
            evidence=evidence,
            verified=True,
            side_effects=[f"file:created:{write_meta['relative_path']}"],
            metadata=write_meta,
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="file_write",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error writing file '{path}': {e}",
        )


@register_tool(
    name="file_list",
    description="List files and directories in a workspace folder. Args: 'path' (relative path, default: '.'), 'recursive' (boolean, default: false), 'pattern' (glob pattern, default: '*').",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative directory path (default: root)"},
            "recursive": {"type": "boolean", "description": "Whether to list subdirectories recursively"},
            "pattern": {"type": "string", "description": "Glob filter pattern (e.g. '*.py', '*.json')"},
        },
    },
    category="filesystem",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
    verification_strategy="FILE_EXISTS",
)
def tool_file_list(args: dict) -> ToolResult:
    """List directory contents with structured metadata."""
    path = str(args.get("path", ".")).strip() or "."
    recursive = bool(args.get("recursive", False))
    pattern = str(args.get("pattern", "*")).strip() or "*"

    try:
        entries = _files.list_dir(path=path, recursive=recursive, pattern=pattern)
        summary_lines = [
            f"{'📁' if e['is_dir'] else '📄'} {e['relative_path']} ({e['size_bytes']:,} bytes)"
            for e in entries
        ]
        evidence = f"Found {len(entries)} items in directory '{path}' matching '{pattern}'."
        return ToolResult.success(
            tool_name="file_list",
            data=entries,
            output="\n".join(summary_lines) if summary_lines else "(Empty directory)",
            evidence=evidence,
            verified=True,
            metadata={"count": len(entries), "path": path, "pattern": pattern},
        )
    except FileNotFoundError:
        return ToolResult.failed(
            tool_name="file_list",
            error_code=ToolErrorCode.TOOL_NOT_FOUND,
            message=f"Directory not found: '{path}'",
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="file_list",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error listing directory '{path}': {e}",
        )


@register_tool(
    name="file_delete",
    description="Delete a file or move it to workspace .trash. Args: 'path' (relative file path), 'permanent' (boolean, default: false).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to delete"},
            "permanent": {"type": "boolean", "description": "Permanently delete without moving to trash (default: false)"},
        },
        "required": ["path"],
    },
    category="filesystem",
    risk_level="high",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="FILE_ABSENT",
)
def tool_file_delete(args: dict) -> ToolResult:
    """Safely delete file with trash protection."""
    path = str(args.get("path", "")).strip()
    permanent = bool(args.get("permanent", False))

    if not path:
        return ToolResult.failed("file_delete", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'path' is required.")

    try:
        del_meta = _files.delete(path, permanent=permanent)
        evidence = (
            f"Permanently deleted '{path}'" if permanent
            else f"Moved '{path}' to workspace trash ({del_meta.get('trash_path', '')})"
        )
        return ToolResult.success(
            tool_name="file_delete",
            data=del_meta,
            output=evidence,
            evidence=evidence,
            verified=del_meta["verified"],
            side_effects=[f"file:deleted:{path}"],
            metadata=del_meta,
        )
    except FileNotFoundError:
        # Idempotent success if file already absent
        return ToolResult.success(
            tool_name="file_delete",
            data={"path": path, "already_absent": True},
            output=f"File '{path}' does not exist on disk.",
            evidence=f"File '{path}' confirmed absent.",
            verified=True,
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="file_delete",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error deleting file '{path}': {e}",
        )


@register_tool(
    name="file_search",
    description="Search workspace files by filename or text content. Args: 'query' (search string), 'search_path' (optional subfolder), 'extension' (optional filter like '.py').",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword or filename substring"},
            "search_path": {"type": "string", "description": "Subdirectory to search (default: root)"},
            "extension": {"type": "string", "description": "File extension filter (e.g. '.py', '.txt')"},
        },
        "required": ["query"],
    },
    category="filesystem",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_file_search(args: dict) -> ToolResult:
    """Search for matching files in workspace by name and content."""
    query = str(args.get("query", "")).strip().lower()
    search_path = str(args.get("search_path", ".")).strip() or "."
    ext = str(args.get("extension", "")).strip().lower()

    if not query:
        return ToolResult.failed("file_search", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'query' is required.")

    try:
        entries = _files.list_dir(path=search_path, recursive=True)
        matches = []
        for e in entries:
            if e["is_dir"]:
                continue
            if ext and not e["name"].lower().endswith(ext):
                continue
            # Match filename or relative path
            if query in e["name"].lower() or query in e["relative_path"].lower():
                matches.append(e)
                continue

            # Match file content for text files (< 2 MB)
            if e["size_bytes"] < 2_000_000:
                try:
                    f_path = Path(e["path"])
                    content = f_path.read_text(encoding="utf-8", errors="ignore")
                    if query in content.lower():
                        matches.append(e)
                except Exception:
                    pass

        evidence = f"Found {len(matches)} matching files for '{query}'."
        return ToolResult.success(
            tool_name="file_search",
            data=matches,
            output=json.dumps(matches, indent=2),
            evidence=evidence,
            verified=True,
            metadata={"count": len(matches), "query": query},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="file_search",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error searching files for '{query}': {e}",
        )

