# tools/batch_file_tool.py — Directory Tree, Batch Search/Replace, & Archive Tool for JARVIS MK37
"""
Provides directory tree visualization, batch regex search and replace across files,
and zip archive operations.
"""
from __future__ import annotations

import logging
import os
import re
import zipfile
from pathlib import Path
from tools.registry import register_tool

logger = logging.getLogger(__name__)


@register_tool(
    name="batch_file_ops",
    description="Perform batch regex file search/replace, directory tree rendering, or zip archive compression/extraction.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["tree_view", "batch_replace", "create_zip", "extract_zip"],
                "description": "Batch operation to perform"
            },
            "target_dir": {"type": "string", "description": "Target root directory path"},
            "pattern": {"type": "string", "description": "Regex pattern or glob file filter"},
            "replace_text": {"type": "string", "description": "Replacement string for batch_replace"},
            "zip_path": {"type": "string", "description": "Archive file path for create_zip/extract_zip"},
            "max_depth": {"type": "integer", "description": "Max depth for tree view (default: 3)"}
        },
        "required": ["action"]
    }
)
def batch_file_ops(args: dict) -> str:
    action = args.get("action", "tree_view")
    target_dir = Path(args.get("target_dir", ".")).resolve()
    pattern = args.get("pattern", "")
    replace_text = args.get("replace_text", "")
    zip_path = args.get("zip_path")
    max_depth = args.get("max_depth", 3)

    if action == "tree_view":
        if not target_dir.exists() or not target_dir.is_dir():
            return f"Error: Directory '{target_dir}' does not exist."

        tree_lines = [f"📁 {target_dir.name}/"]

        def _walk_tree(dir_path: Path, prefix: str, current_depth: int):
            if current_depth > max_depth:
                return
            try:
                entries = sorted(list(dir_path.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
                # Filter out hidden/pycache/git dirs
                entries = [e for e in entries if not e.name.startswith(".") and e.name != "__pycache__"]
                count = len(entries)
                for idx, entry in enumerate(entries):
                    is_last = (idx == count - 1)
                    connector = "└── " if is_last else "├── "
                    if entry.is_dir():
                        tree_lines.append(f"{prefix}{connector}📁 {entry.name}/")
                        new_prefix = prefix + ("    " if is_last else "│   ")
                        _walk_tree(entry, new_prefix, current_depth + 1)
                    else:
                        tree_lines.append(f"{prefix}{connector}📄 {entry.name}")
            except Exception as e:
                tree_lines.append(f"{prefix}⚠️ Error reading dir: {e}")

        _walk_tree(target_dir, "", 1)
        return "\n".join(tree_lines[:150]) + ("\n... (truncated)" if len(tree_lines) > 150 else "")

    elif action == "batch_replace":
        if not pattern:
            return "Error: 'pattern' parameter is required for batch_replace."
        if not target_dir.exists():
            return f"Error: Target path '{target_dir}' does not exist."

        modified_files = []
        rx = re.compile(pattern)
        
        files_to_check = [target_dir] if target_dir.is_file() else list(target_dir.rglob("*"))
        for f in files_to_check:
            if f.is_file() and not f.name.startswith(".") and "__pycache__" not in f.parts:
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    if rx.search(content):
                        new_content = rx.sub(replace_text, content)
                        f.write_text(new_content, encoding="utf-8")
                        modified_files.append(str(f.relative_to(target_dir if target_dir.is_dir() else target_dir.parent)))
                except Exception as e:
                    logger.debug('Suppressed exception: %s', e)
        return f"✅ Batch replace complete. Modified {len(modified_files)} file(s):\n" + "\n".join(f"- {m}" for m in modified_files[:20])

    elif action == "create_zip":
        archive = Path(zip_path or "archive.zip").resolve()
        if not target_dir.exists():
            return f"Error: Target path '{target_dir}' does not exist."

        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            if target_dir.is_file():
                zf.write(target_dir, arcname=target_dir.name)
            else:
                for root, dirs, files in os.walk(target_dir):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                    for file in files:
                        full_p = Path(root) / file
                        arcname = full_p.relative_to(target_dir)
                        zf.write(full_p, arcname=arcname)
        return f"✅ Created Zip Archive: '{archive}' ({archive.stat().st_size / 1024:.1f} KB)"

    elif action == "extract_zip":
        if not zip_path or not Path(zip_path).exists():
            return f"Error: Zip archive '{zip_path}' does not exist."
        dest = Path(target_dir or ".").resolve()
        dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest)
        return f"✅ Extracted '{zip_path}' to '{dest}'."

    return f"Unknown action '{action}'."
