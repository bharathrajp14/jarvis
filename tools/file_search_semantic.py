# tools/file_search_semantic.py — Semantic File Search Tool for JARVIS
"""
Fast local semantic file search tool.
Matches natural language queries against workspace filenames, extensions, and paths.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from tools.registry import register_tool


def semantic_file_search(query: str, root_dir: Optional[Path] = None, max_results: int = 15) -> List[Dict[str, Any]]:
    """Match natural language query against workspace files using fuzzy keyword scoring."""
    if not query or not query.strip():
        return []

    target_root = root_dir or Path.cwd()
    query_terms = [t.lower() for t in query.strip().split() if len(t) > 1]

    matches = []
    for root, dirs, files in os.walk(target_root):
        # Ignore hidden and build directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", "venv")]
        for f in files:
            fp = Path(root) / f
            rel_path = str(fp.relative_to(target_root)).lower()

            score = 0
            for term in query_terms:
                if term in rel_path:
                    score += 2 if term in f.lower() else 1

            if score > 0:
                matches.append({
                    "score": score,
                    "filename": f,
                    "path": str(fp),
                    "relative_path": str(fp.relative_to(target_root)),
                })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:max_results]


@register_tool(
    name="semantic_file_search",
    description="Search workspace files by natural language keywords, filename patterns, or extensions.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or file pattern"}
        },
        "required": ["query"]
    }
)
@register_tool(
    name="file_search_semantic",
    description="Search workspace files by natural language keywords, filename patterns, or extensions.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or file pattern"}
        },
        "required": ["query"]
    }
)
def file_search_semantic_action(args: Dict[str, Any]) -> str:

    """Main tool handler for semantic file search."""
    if isinstance(args, str):
        query = args.strip()
    else:
        query = str(args.get("query") or args.get("q") or args.get("pattern") or args.get("filename") or "").strip()
    
    res = semantic_file_search(query)
    if not res:
        return f"No matching files found for query '{query}'."

    lines = [f"Found {len(res)} matching files for '{query}':"]
    for m in res:
        lines.append(f"• {m['relative_path']} (score: {m['score']})")
    return "\n".join(lines)
