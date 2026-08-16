# tools/recall_tools.py — Total Recall Voice Note Capture Tool Wrapper
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from .registry import register_tool
from actions.galaxy import build_galaxy_graph, CAPTURES_DIR


@register_tool(
    name="remember_that",
    description="Save a new memory note to disk by voice or text ('Remember that...'), live-spawning a node on the 3D Knowledge Galaxy.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Information or memory note to save and index into knowledge brain."}
        },
        "required": ["text"]
    }
)
def tool_remember_that(text: str) -> str:
    text = text.strip()
    if not text:
        return "Please provide something to remember, sir."

    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    words = re.findall(r"\w+", text)
    title_slug = "_".join(words[:5]).lower() if words else "note"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{title_slug}.md"
    file_path = CAPTURES_DIR / filename

    content = f"# {text[:40]}...\n\nCaptured: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{text}\n"
    file_path.write_text(content, encoding="utf-8")

    # Refresh 3D graph data
    graph = build_galaxy_graph()

    return f"Very good, sir. Saved note '{filename}' and indexed it into your 3D Knowledge Galaxy ({len(graph['nodes'])} total nodes)."
