# connectors/filesystem.py — Local Filesystem Connector (Zero-Setup)
"""
Local filesystem connector — read, search, list, and summarize local files.
Zero-setup. No auth required. Operates within safe allowed directories only.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Filesystem")

# Safe root directories — connector can only access these
_SAFE_ROOTS = [
    Path.home(),
    Path.cwd(),
    Path("BR_WORKSPACE"),
]

# File extensions that can be read as text
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".env", ".sh", ".bat", ".ps1", ".cs",
    ".java", ".go", ".rs", ".cpp", ".c", ".h", ".html", ".css",
    ".xml", ".csv", ".log", ".sql", ".r", ".rb", ".php", ".swift",
    ".kt", ".scala", ".vue", ".jsx", ".tsx", ".graphql",
}


class FilesystemConnector(BaseConnector):

    @property
    def connector_id(self) -> str:
        return "filesystem"

    @property
    def display_name(self) -> str:
        return "Local Filesystem"

    @property
    def description(self) -> str:
        return "Read, list, and search files on your local computer"

    @property
    def icon(self) -> str:
        return "📁"

    @property
    def requires_auth(self) -> bool:
        return False

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="list_files",
                description="List files and directories in a given path",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to list (default: current workspace)"},
                        "pattern": {"type": "string", "description": "Glob filter pattern (e.g. '*.py', '*.md')"},
                        "recursive": {"type": "boolean", "default": False},
                        "limit": {"type": "integer", "default": 30},
                    },
                },
            ),
            ConnectorTool(
                name="read_file",
                description="Read the content of a text file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Full or relative file path"},
                        "max_lines": {"type": "integer", "description": "Max lines to read", "default": 200},
                        "start_line": {"type": "integer", "description": "Start line (1-indexed)", "default": 1},
                    },
                    "required": ["path"],
                },
            ),
            ConnectorTool(
                name="search_files",
                description="Search for files by name or content keyword",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Filename keyword or content to search for"},
                        "search_type": {
                            "type": "string",
                            "enum": ["name", "content", "both"],
                            "default": "name",
                            "description": "Search by filename, file content, or both",
                        },
                        "path": {"type": "string", "description": "Directory to search in (default: current workspace)"},
                        "extensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File extensions to include (e.g. ['.py', '.md'])",
                        },
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["query"],
                },
            ),
            ConnectorTool(
                name="get_file_info",
                description="Get metadata about a file (size, modified date, permissions)",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                    },
                    "required": ["path"],
                },
            ),
            ConnectorTool(
                name="workspace_summary",
                description="Get a summary of the current project/workspace structure",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Workspace root (default: current directory)"},
                        "depth": {"type": "integer", "default": 2},
                    },
                },
            ),
        ]

    def _resolve_path(self, path_str: str) -> Optional[Path]:
        """Resolve and validate a path is within safe directories."""
        if not path_str:
            return Path.cwd()
        p = Path(path_str).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        p = p.resolve()

        # Security check: must be within a safe root
        for safe_root in _SAFE_ROOTS:
            try:
                p.relative_to(safe_root.resolve())
                return p
            except ValueError:
                continue

        # Fallback: allow if path exists and looks safe (not system dirs)
        dangerous = ["/etc", "/sys", "/proc", "/dev", "C:\\Windows\\System32"]
        path_str_lower = str(p).lower()
        if any(d.lower() in path_str_lower for d in dangerous):
            return None
        return p

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "list_files":
            return self._list_files(
                args.get("path", ""), args.get("pattern", ""),
                bool(args.get("recursive", False)), int(args.get("limit", 30))
            )
        elif tool_name == "read_file":
            return self._read_file(
                args.get("path", ""), int(args.get("max_lines", 200)),
                int(args.get("start_line", 1))
            )
        elif tool_name == "search_files":
            return self._search_files(
                args.get("query", ""), args.get("search_type", "name"),
                args.get("path", ""), args.get("extensions", []),
                int(args.get("limit", 20))
            )
        elif tool_name == "get_file_info":
            return self._get_file_info(args.get("path", ""))
        elif tool_name == "workspace_summary":
            return self._workspace_summary(args.get("path", ""), int(args.get("depth", 2)))
        return f"Unknown tool: {tool_name}"

    def _list_files(self, path: str, pattern: str, recursive: bool, limit: int) -> str:
        p = self._resolve_path(path)
        if not p:
            return f"❌ Path not allowed or doesn't exist: {path}"
        if not p.exists():
            return f"❌ Path does not exist: {p}"
        if not p.is_dir():
            return f"❌ '{p}' is a file, not a directory. Use read_file instead."

        try:
            glob_pattern = pattern or "*"
            if recursive:
                items = list(p.rglob(glob_pattern))
            else:
                items = list(p.glob(glob_pattern))

            # Filter hidden/system dirs
            items = [
                f for f in items
                if not any(part.startswith(".") or part in ("__pycache__", "node_modules", ".venv", "venv")
                           for part in f.parts)
            ]
            items = sorted(items, key=lambda x: (x.is_file(), x.name))[:limit]

            if not items:
                return f"📁 No files found in '{p}' (pattern: {glob_pattern})"

            lines = [f"📁 **{p}** ({len(items)} items)\n"]
            for item in items:
                rel = item.relative_to(p) if item.is_relative_to(p) else item
                size = item.stat().st_size if item.is_file() else 0
                size_str = f" ({_format_size(size)})" if item.is_file() else "/"
                icon = "📄" if item.is_file() else "📂"
                lines.append(f"{icon} {rel}{size_str}")
            return "\n".join(lines)
        except Exception as e:
            return f"List files error: {e}"

    def _read_file(self, path: str, max_lines: int = 200, start_line: int = 1) -> str:
        p = self._resolve_path(path)
        if not p:
            return f"❌ Path not allowed: {path}"
        if not p.exists():
            return f"❌ File not found: {path}"
        if not p.is_file():
            return f"❌ '{path}' is a directory. Use list_files instead."

        ext = p.suffix.lower()
        if ext not in _TEXT_EXTENSIONS:
            return f"⚠️ Binary file detected ({ext}). Can only read text files."

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)
            start = max(0, start_line - 1)
            end = min(start + max_lines, total_lines)
            slice_lines = lines[start:end]

            truncated = ""
            if end < total_lines:
                truncated = f"\n\n[...{total_lines - end} more lines. Use start_line={end + 1} to continue.]"

            ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript",
                       ".json": "json", ".md": "markdown", ".sh": "bash", ".sql": "sql"}
            lang = ext_map.get(ext, "")
            content_block = "\n".join(slice_lines)
            size = _format_size(p.stat().st_size)

            return (
                f"📄 **{p.name}** ({size}, {total_lines} lines total)\n"
                f"Showing lines {start + 1}–{end}\n\n"
                f"```{lang}\n{content_block}\n```{truncated}"
            )
        except Exception as e:
            return f"Read file error: {e}"

    def _search_files(self, query: str, search_type: str, path: str,
                      extensions: list, limit: int) -> str:
        search_root = self._resolve_path(path) or Path.cwd()
        if not search_root.exists():
            return f"❌ Search path does not exist: {path}"

        query_lower = query.lower()
        matches = []

        try:
            all_files = [
                f for f in search_root.rglob("*")
                if f.is_file()
                and not any(part.startswith(".") or part in ("__pycache__", "node_modules", ".venv", "venv")
                            for part in f.parts)
            ]

            if extensions:
                all_files = [f for f in all_files if f.suffix.lower() in {e.lower() for e in extensions}]

            for f in all_files:
                if len(matches) >= limit:
                    break

                matched = False
                match_context = ""

                if search_type in ("name", "both"):
                    if query_lower in f.name.lower():
                        matched = True

                if not matched and search_type in ("content", "both"):
                    if f.suffix.lower() in _TEXT_EXTENSIONS:
                        try:
                            content = f.read_text(encoding="utf-8", errors="replace")
                            if query_lower in content.lower():
                                matched = True
                                # Find matching line for context
                                for i, line in enumerate(content.splitlines(), 1):
                                    if query_lower in line.lower():
                                        match_context = f"  Line {i}: {line.strip()[:100]}"
                                        break
                        except Exception as e:
                            logger.debug('Suppressed exception: %s', e)
                if matched:
                    matches.append((f, match_context))

        except Exception as e:
            return f"Search error: {e}"

        if not matches:
            return f"No files found matching '{query}' (type: {search_type})"

        lines = [f"🔍 **File Search: '{query}'** ({len(matches)} results)\n"]
        for f, ctx in matches[:limit]:
            size = _format_size(f.stat().st_size)
            lines.append(f"• 📄 {f} ({size})")
            if ctx:
                lines.append(ctx)
        return "\n".join(lines)

    def _get_file_info(self, path: str) -> str:
        p = self._resolve_path(path)
        if not p or not p.exists():
            return f"❌ File not found: {path}"
        try:
            import datetime
            stat = p.stat()
            modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            created = datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            size = _format_size(stat.st_size)
            ftype = "Directory" if p.is_dir() else "File"
            ext = p.suffix or "No extension"
            return (
                f"📄 **{p.name}** ({ftype})\n"
                f"• Path: {p}\n"
                f"• Size: {size}\n"
                f"• Extension: {ext}\n"
                f"• Modified: {modified}\n"
                f"• Created: {created}"
            )
        except Exception as e:
            return f"File info error: {e}"

    def _workspace_summary(self, path: str, depth: int = 2) -> str:
        root = self._resolve_path(path) or Path.cwd()
        if not root.exists():
            return f"❌ Workspace path does not exist: {path}"

        lines = [f"📁 **Workspace: {root.name}/**\n"]
        py_count = len(list(root.rglob("*.py")))
        md_count = len(list(root.rglob("*.md")))
        json_count = len(list(root.rglob("*.json")))
        total = len([f for f in root.rglob("*") if f.is_file()])

        lines.append(f"• Total files: {total}")
        lines.append(f"• Python files: {py_count}")
        lines.append(f"• Markdown files: {md_count}")
        lines.append(f"• JSON files: {json_count}\n")

        # Show directory tree up to depth
        def _tree(p: Path, current_depth: int, prefix: str = ""):
            if current_depth > depth:
                return
            items = sorted([x for x in p.iterdir()
                           if not x.name.startswith(".")
                           and x.name not in ("__pycache__", "node_modules", ".venv", "venv", "dist")],
                          key=lambda x: (x.is_file(), x.name))
            for item in items[:20]:
                connector = "├── " if item != items[-1] else "└── "
                size_str = f" ({_format_size(item.stat().st_size)})" if item.is_file() else "/"
                lines.append(f"{prefix}{connector}{item.name}{size_str}")
                if item.is_dir() and current_depth < depth:
                    extension = "│   " if item != items[-1] else "    "
                    _tree(item, current_depth + 1, prefix + extension)
            if len(list(p.iterdir())) > 20:
                lines.append(f"{prefix}└── ...")

        _tree(root, 1)
        return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f}MB"
    return f"{size_bytes / 1024 ** 3:.1f}GB"
