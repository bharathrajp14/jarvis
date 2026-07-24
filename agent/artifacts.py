# agent/artifacts.py — Antigravity-Style Markdown Artifact Generator
"""
Artifact Document Generator for BR JARVIS.
Renders GitHub-Flavored Markdown documents with alerts (> [!NOTE]), mermaid diagrams,
clickable file links (file:///...), code diffs, and carousel blocks.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class ArtifactMetadata:
    summary: str
    user_facing: bool = True
    request_feedback: bool = False
    created_at: float = field(default_factory=time.time)


class ArtifactDocument:
    """Represents a structured Markdown artifact document."""

    def __init__(self, title: str, filepath: str | Path, metadata: Optional[ArtifactMetadata] = None):
        self.title = title
        self.filepath = Path(filepath)
        self.metadata = metadata or ArtifactMetadata(summary=title)
        self.sections: List[Dict[str, str]] = []
        self._content_chunks: List[str] = []

    def add_alert(self, alert_type: str, text: str) -> ArtifactDocument:
        """
        Add a GitHub-style alert callout: NOTE, TIP, IMPORTANT, WARNING, CAUTION.
        """
        atype = alert_type.upper()
        if atype not in ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"):
            atype = "NOTE"
        self._content_chunks.append(f"> [!{atype}]\n> {text.replace('\n', '\n> ')}")
        return self

    def add_section(self, heading: str, body: str, level: int = 2) -> ArtifactDocument:
        prefix = "#" * max(1, min(6, level))
        self._content_chunks.append(f"{prefix} {heading}\n\n{body.strip()}")
        return self

    def add_mermaid_diagram(self, mermaid_code: str) -> ArtifactDocument:
        self._content_chunks.append(f"```mermaid\n{mermaid_code.strip()}\n```")
        return self

    def add_code_diff(self, old_code: str, new_code: str, filename: str = "") -> ArtifactDocument:
        diff_lines = []
        if filename:
            diff_lines.append(f"--- a/{filename}")
            diff_lines.append(f"+++ b/{filename}")
        for l in old_code.splitlines():
            diff_lines.append(f"-{l}")
        for l in new_code.splitlines():
            diff_lines.append(f"+{l}")
        self._content_chunks.append("```diff\n" + "\n".join(diff_lines) + "\n```")
        return self

    def render(self) -> str:
        header = f"# {self.title}\n\n"
        body = "\n\n".join(self._content_chunks)
        return header + body

    def save(self) -> Path:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.render()
        self.filepath.write_text(content, encoding="utf-8")
        return self.filepath.resolve()


def make_file_link(filepath: str | Path, text: str | None = None, start_line: int | None = None, end_line: int | None = None) -> str:
    """Format clickable file:// markdown link."""
    p = Path(filepath).resolve()
    uri = p.as_uri()
    if start_line is not None:
        if end_line is not None and end_line != start_line:
            uri += f"#L{start_line}-L{end_line}"
        else:
            uri += f"#L{start_line}"
    label = text or p.name
    return f"[{label}]({uri})"
