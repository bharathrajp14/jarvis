# actions/galaxy.py — 3D Knowledge Galaxy Data & RAG Graph Engine
"""
Scans markdown notes and long-term memory to build 3D force graph data (graph-data.js).
Supports node search, camera fly-to-source indexing, and live node creation.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from brjarvis.core.paths import paths

BASE_DIR = paths.PROJECT_ROOT
NOTES_DIR = paths.WORKSPACE_ROOT / "notes"
CAPTURES_DIR = paths.CAPTURE_ROOT
WEB_DIR = paths.PROJECT_ROOT / "assets" / "static" / "web"
DATA_JS_PATH = WEB_DIR / "graph-data.js"


def ensure_dirs() -> None:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)


def build_galaxy_graph() -> dict[str, Any]:
    """
    Scans all .md files in notes/ and captures/, building node & link structure.
    Returns dict: {"nodes": [...], "links": [...]}
    """
    ensure_dirs()

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    title_to_id: dict[str, int] = {}

    files: list[Path] = []
    scan_dirs = [
        paths.PROJECT_ROOT / "notes",
        paths.WORKSPACE_ROOT / "notes",
        CAPTURES_DIR,
    ]
    for d in scan_dirs:
        if d.exists():
            files.extend(list(d.glob("**/*.md")))

    # Deduplicate file paths
    files = list(dict.fromkeys(files))

    if not files:
        # Create a sample welcome note if empty
        sample_note = NOTES_DIR / "welcome.md"
        sample_note.write_text(
            "# Welcome to BR JARVIS 3D Knowledge Galaxy\n"
            "This is your personal knowledge brain. Ask JARVIS questions to fly through notes.\n",
            encoding="utf-8"
        )
        files.append(sample_note)

    for idx, filepath in enumerate(files):
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = ""

        label = filepath.stem.replace("_", " ").title()
        group = filepath.parent.name
        excerpt = content[:700]

        node_entry = {
            "id": idx,
            "label": label,
            "group": group,
            "path": str(filepath.relative_to(BASE_DIR)),
            "excerpt": excerpt,
        }
        nodes.append(node_entry)
        title_to_id[label.lower()] = idx
        title_to_id[filepath.stem.lower()] = idx

    # Build links between nodes based on title mentions or shared words
    for node in nodes:
        node_id = node["id"]
        excerpt_lower = node["excerpt"].lower()
        for other_title, other_id in title_to_id.items():
            if node_id != other_id and len(other_title) > 3 and other_title in excerpt_lower:
                links.append({"source": node_id, "target": other_id})

    graph_data = {"nodes": nodes, "links": links}

    # Save to web/graph-data.js for 3D viewer
    js_content = f"window.GRAPH = {json.dumps(graph_data, indent=2, ensure_ascii=False)};"
    try:
        DATA_JS_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_JS_PATH.write_text(js_content, encoding="utf-8")
        src_web_js = paths.SOURCE_ROOT / "web" / "graph-data.js"
        if src_web_js.parent.exists():
            src_web_js.write_text(js_content, encoding="utf-8")
    except Exception as e:
        pass

    return graph_data


_cached_galaxy_graph: dict[str, Any] | None = None
_cached_galaxy_time: float = 0.0

def query_galaxy(query: str, top_k: int = 6) -> dict[str, Any]:
    """
    Score notes against a user query using keyword & title overlap.
    Returns dict: {"answer": str, "source_nodes": [int]}
    """
    global _cached_galaxy_graph, _cached_galaxy_time
    now = time.time()
    if _cached_galaxy_graph is None or (now - _cached_galaxy_time) > 60.0:
        _cached_galaxy_graph = build_galaxy_graph()
        _cached_galaxy_time = now

    graph = _cached_galaxy_graph
    nodes = graph.get("nodes", [])

    if not nodes:
        return {"answer": "No notes found in knowledge galaxy, sir.", "source_nodes": []}

    query_words = set(re.findall(r"\w+", query.lower()))

    scored_nodes = []
    for node in nodes:
        text = f"{node['label']} {node['excerpt']}".lower()
        score = 0
        for word in query_words:
            if len(word) > 2:
                if word in node['label'].lower():
                    score += 5
                if word in text:
                    score += 1
        if score > 0:
            scored_nodes.append((score, node))

    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    top_matches = [node for _, node in scored_nodes[:top_k]]

    if not top_matches:
        top_matches = nodes[:top_k]

    source_ids = [n["id"] for n in top_matches]
    excerpts = [f"- {n['label']}: {n['excerpt'][:150]}..." for n in top_matches]

    summary = "\n".join(excerpts)
    return {
        "summary": summary,
        "source_nodes": source_ids,
        "count": len(nodes),
    }
