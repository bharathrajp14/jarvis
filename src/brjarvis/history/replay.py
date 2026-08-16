# history/replay.py — Session Replay and Multiformat Exporter
"""
Session replay and export utilities for JARVIS MK37.

Reconstructs WorkingMemory objects from stored turns and exports
sessions as formatted Markdown or standalone HTML documents.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_session(session_id: str, store: Any = None) -> Any:
    """Reconstruct a WorkingMemory object from stored turns.

    Args:
        session_id: the session ID to load
        store: SessionStore instance (creates a temporary one if None)

    Returns:
        A WorkingMemory instance with all turns replayed.
    """
    if store is None:
        from history.session_store import SessionStore
        store = SessionStore()

    session = store.get_session(session_id)
    if session is None:
        raise ValueError(f"Session '{session_id}' not found")

    from memory.working import WorkingMemory
    wm = WorkingMemory()

    for turn in session.get("turns", []):
        role = turn.get("role", "user")
        content = turn.get("content", "")

        tool_name = turn.get("tool_name")
        tool_result = turn.get("tool_result")
        if tool_name and tool_result and role == "user":
            content = f"[Tool Result for '{tool_name}']:\n{tool_result}"
        elif tool_name and role == "assistant":
            tool_args = turn.get("tool_args", "")
            content = f"[Tool Call: {tool_name}({tool_args})]\n{content}"

        if content:
            wm.add(role, content)

    return wm


def replay_as_context(session_id: str, store: Any = None) -> str:
    """Return a formatted string block of a session suitable for system prompt injection."""
    if store is None:
        from history.session_store import SessionStore
        store = SessionStore()

    session = store.get_session(session_id)
    if session is None:
        return f"[Session '{session_id}' not found]"

    lines: list[str] = []
    lines.append(f"## Replayed Session: {session_id}")
    lines.append(f"Mode: {session.get('mode', 'general')} | Backend: {session.get('backend', 'unknown')}")

    start_ts = session.get("start_ts")
    if start_ts:
        dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        lines.append(f"Started: {dt.strftime('%Y-%m-%d %H:%M UTC')}")

    summary = session.get("summary")
    if summary:
        lines.append(f"Summary: {summary}")

    lines.append("")

    for turn in session.get("turns", []):
        ts = turn.get("ts", 0)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        time_str = dt.strftime("%H:%M:%S")
        role = turn.get("role", "?").upper()
        content = turn.get("content", "")[:300]

        tool_name = turn.get("tool_name")
        if tool_name:
            lines.append(f"[{time_str}] {role}: [Tool: {tool_name}] {content}")
        else:
            lines.append(f"[{time_str}] {role}: {content}")

    return "\n".join(lines)


def export_markdown(session_id: str, output_path: str | Path, store: Any = None) -> Path:
    """Export a session as a readable Markdown file with timestamps and collapsible tool calls."""
    if store is None:
        from history.session_store import SessionStore
        store = SessionStore()

    session = store.get_session(session_id)
    if session is None:
        raise ValueError(f"Session '{session_id}' not found")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# JARVIS MK37 — Session Export")
    lines.append("")
    lines.append(f"**Session ID:** `{session_id}`")
    lines.append(f"**Mode:** {session.get('mode', 'general')}")
    lines.append(f"**Backend:** {session.get('backend', 'unknown')}")
    lines.append(f"**Turns:** {session.get('turn_count', 0)}")

    start_ts = session.get("start_ts")
    end_ts = session.get("end_ts")
    if start_ts:
        dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        lines.append(f"**Started:** {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if end_ts:
        dt = datetime.fromtimestamp(end_ts, tz=timezone.utc)
        lines.append(f"**Ended:** {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if start_ts:
            duration = end_ts - start_ts
            mins = duration // 60
            secs = duration % 60
            lines.append(f"**Duration:** {mins}m {secs}s")

    summary = session.get("summary")
    if summary:
        lines.append("")
        lines.append("## Summary")
        lines.append(summary)

    tags = session.get("tags", [])
    if tags:
        lines.append(f"**Tags:** {', '.join(tags)}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Conversation Transcript")
    lines.append("")

    for turn in session.get("turns", []):
        ts = turn.get("ts", 0)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        tool_name = turn.get("tool_name")
        tool_args = turn.get("tool_args")
        tool_result = turn.get("tool_result")
        backend = turn.get("backend")
        latency = turn.get("latency_ms")

        role_display = "🧑 **User**" if role == "user" else "🤖 **JARVIS**"
        meta_parts = [f"`{time_str}`"]
        if backend:
            meta_parts.append(f"backend: {backend}")
        if latency:
            meta_parts.append(f"{latency}ms")
        meta = " | ".join(meta_parts)

        lines.append(f"### {role_display} — {meta}")
        lines.append("")

        if content:
            lines.append(content)
            lines.append("")

        if tool_name:
            lines.append(f"<details><summary>🔧 <b>Tool Call:</b> <code>{tool_name}</code></summary>\n")
            if tool_args:
                lines.append(f"**Arguments:**\n```json\n{tool_args}\n```\n")
            if tool_result:
                lines.append(f"**Result Output:**\n```text\n{tool_result[:2000]}\n```\n")
            lines.append("</details>\n")

        lines.append("---")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def export_html(session_id: str, output_path: str | Path, store: Any = None) -> Path:
    """Export a session as a self-contained HTML report with dark/light themes."""
    if store is None:
        from history.session_store import SessionStore
        store = SessionStore()

    session = store.get_session(session_id)
    if session is None:
        raise ValueError(f"Session '{session_id}' not found")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    turns_html = []
    for turn in session.get("turns", []):
        role = turn.get("role", "user")
        content = html.escape(turn.get("content", ""))
        tool_name = turn.get("tool_name")
        tool_result = html.escape(turn.get("tool_result", "")[:1500]) if turn.get("tool_result") else ""

        cls = "user-msg" if role == "user" else "jarvis-msg"
        tool_block = ""
        if tool_name:
            tool_block = f"""
            <details class="tool-details">
                <summary>🔧 Tool Call: <code>{html.escape(tool_name)}</code></summary>
                <pre class="tool-output">{tool_result}</pre>
            </details>
            """

        turns_html.append(f"""
        <div class="message {cls}">
            <div class="role-badge">{role.upper()}</div>
            <div class="body">{content}</div>
            {tool_block}
        </div>
        """)

    body_content = "\n".join(turns_html)

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>JARVIS Session Export — {session_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; max-width: 900px; margin: 0 auto; }}
        h1 {{ color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }}
        .message {{ background: #1e293b; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #64748b; }}
        .user-msg {{ border-left-color: #3b82f6; }}
        .jarvis-msg {{ border-left-color: #10b981; }}
        .role-badge {{ font-size: 0.75rem; font-weight: bold; color: #94a3b8; margin-bottom: 0.5rem; }}
        .body {{ white-space: pre-wrap; line-height: 1.5; }}
        .tool-details {{ margin-top: 0.8rem; background: #0f172a; padding: 0.5rem; border-radius: 4px; }}
        .tool-output {{ font-family: monospace; font-size: 0.85rem; color: #a7f3d0; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>JARVIS Session {session_id}</h1>
    <p><b>Mode:</b> {session.get('mode')} | <b>Backend:</b> {session.get('backend')} | <b>Turns:</b> {session.get('turn_count')}</p>
    <hr style="border-color:#334155;">
    {body_content}
</body>
</html>"""

    out.write_text(html_page, encoding="utf-8")
    return out
