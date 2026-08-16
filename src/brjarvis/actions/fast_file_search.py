# actions/fast_file_search.py — Advanced Desktop File Searching for BR-JARVIS
"""
Pika Voice-style Advanced Desktop File Search engine.
Searches files by name, extension, or inside text contents across system drives.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import glob
from pathlib import Path

logger = logging.getLogger(__name__)

_EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", "AppData", "Windows", "Program Files", "Program Files (x86)", "$Recycle.Bin", ".venv", "venv"}


def search_files_by_name(query: str, root_dir: str = "", max_results: int = 20) -> list[str]:
    """Fast recursive filename search."""
    if not root_dir or not os.path.exists(root_dir):
        from brjarvis.core.paths import paths
        root_dir = str(paths.WORKSPACE_ROOT)

    query_low = query.lower().strip()
    results = []

    try:
        for root, dirs, files in os.walk(root_dir):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in _EXCLUDE_DIRS and not d.startswith(".")]

            for f in files:
                if query_low in f.lower():
                    results.append(os.path.join(root, f))
                    if len(results) >= max_results:
                        return results
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
    return results[:max_results]


def search_file_contents(query: str, search_path: str = "", extension: str = "", max_results: int = 15) -> list[dict]:
    """Search inside text files for target string."""
    if not search_path or not os.path.exists(search_path):
        from brjarvis.core.paths import paths
        search_path = str(paths.WORKSPACE_ROOT)

    query_low = query.lower().strip()
    ext_pattern = f"*.{extension.lstrip('.')}" if extension else "*.*"
    matches = []

    try:
        pattern = os.path.join(search_path, "**", ext_pattern)
        for filepath in glob.glob(pattern, recursive=True):
            if len(matches) >= max_results:
                break
            p = Path(filepath)
            if any(part in _EXCLUDE_DIRS or part.startswith(".") for part in p.parts):
                continue
            if p.suffix.lower() in (".exe", ".dll", ".png", ".jpg", ".zip", ".mp3", ".mp4", ".pdf", ".docx", ".xlsx", ".pyc"):
                continue

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                if query_low in content.lower():
                    idx = content.lower().find(query_low)
                    start = max(0, idx - 40)
                    end = min(len(content), idx + len(query) + 60)
                    snippet = content[start:end].replace("\n", " ").strip()
                    matches.append({
                        "path": str(p),
                        "name": p.name,
                        "snippet": f"...{snippet}...",
                    })
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
    return matches[:max_results]


def fast_file_search_action(action: str = "name", query: str = "", search_path: str = "", extension: str = "") -> str:
    """Tool function for high-speed file searching."""
    act = (action or "name").lower().strip()
    if not query:
        return "ERROR: Query parameter is required."

    if act in ("name", "file", "filename"):
        files = search_files_by_name(query, root_dir=search_path)
        if not files:
            return f"No files matching '{query}' were found."
        lines = [f"- `{f}`" for f in files]
        return f"🔍 Found {len(files)} matching file(s):\n" + "\n".join(lines)
    elif act in ("content", "text", "grep"):
        results = search_file_contents(query, search_path=search_path, extension=extension)
        if not results:
            return f"No file contents matching '{query}' were found."
        lines = [f"- **{r['name']}** (`{r['path']}`): {r['snippet']}" for r in results]
        return f"📄 Found {len(results)} file(s) containing '{query}':\n" + "\n".join(lines)
    else:
        return f"ERROR: Unknown search action '{action}'"
