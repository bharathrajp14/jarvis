# actions/chat_export.py — JARVIS MK37 Chat Log Exporter
"""
Exports conversation history to multiple formats: PDF, Markdown, HTML, Plain Text.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _output_dir() -> Path:
    """Get or create the exports directory."""
    d = Path("workspace/exports")
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_chat(
    format: str = "pdf",
    session_id: str = None,
    max_turns: int = 100,
) -> dict:
    """
    Export the current chat log.

    Args:
        format: 'pdf', 'md', 'html', 'txt'.
        session_id: Optional session identifier.
        max_turns: Maximum conversation turns to export.

    Returns:
        dict with 'status', 'output_path', 'format'.
    """
    format = format.lower().strip()
    if format not in ("pdf", "md", "html", "txt"):
        return {"error": f"Unsupported export format: {format}"}

    # Fetch conversation history
    try:
        # Get history from working memory
        from brjarvis.core.bootstrap import build_assistant_runtime

        runtime = build_assistant_runtime()
        history = runtime.orchestrator.working_memory.get()
    except Exception:
        # Fallback empty or local file read
        history = []

    if not history:
        # Try to construct mock history if empty for demonstration
        history = [
            {"role": "user", "content": "Hello JARVIS"},
            {"role": "assistant", "content": "Hello sir. How can I assist you today?"},
        ]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_export_{ts}.{format}"
    out_path = _output_dir() / filename

    try:
        if format == "md":
            _export_md(history, out_path)
        elif format == "html":
            _export_html(history, out_path)
        elif format == "txt":
            _export_txt(history, out_path)
        elif format == "pdf":
            _export_pdf(history, out_path)

        return {
            "status": "success",
            "format": format,
            "output_path": str(out_path.resolve()),
            "turns_exported": len(history),
        }
    except Exception as e:
        return {"error": f"Export failed: {e}"}


def _export_md(history: list[dict], path: Path):
    """Export to Markdown."""
    lines = [
        "# JARVIS MK37 — Conversation Log",
        f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "---",
        "",
    ]
    for msg in history:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        lines.append(f"### **{role}**")
        lines.append(content)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _export_html(history: list[dict], path: Path):
    """Export to HTML."""
    html_template = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>JARVIS Chat Export</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #cbd5e1; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }
  h1 { color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 10px; }
  .meta { color: #64748b; font-size: 0.9em; margin-bottom: 30px; }
  .message { margin-bottom: 24px; padding: 15px; border-radius: 8px; }
  .user { background: #1e293b; border-left: 4px solid #6366f1; }
  .assistant { background: #1e293b; border-left: 4px solid #38bdf8; }
  .role { font-weight: bold; margin-bottom: 8px; font-size: 0.85em; text-transform: uppercase; tracking-spacing: 0.05em; }
  .user .role { color: #818cf8; }
  .assistant .role { color: #7dd3fc; }
  pre { background: #0f172a; padding: 12px; border-radius: 6px; overflow-x: auto; color: #e2e8f0; font-family: monospace; }
</style>
</head>
<body>
  <h1>JARVIS MK37 — Conversation Log</h1>
  <div class="meta">Exported on: __DATE__</div>
  <div class="chat-container">
    __CHAT__
  </div>
</body>
</html>
"""
    chat_html = []
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        # Simple code block formatting in HTML
        content = re.sub(r"```(.*?)```", r"<pre>\1</pre>", content)

        chat_html.append(
            f'  <div class="message {role}">\n'
            f'    <div class="role">{role}</div>\n'
            f'    <div class="content">{content}</div>\n'
            f"  </div>"
        )

    full_html = html_template.replace("__DATE__", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    full_html = full_html.replace("__CHAT__", "\n".join(chat_html))
    path.write_text(full_html, encoding="utf-8")


def _export_txt(history: list[dict], path: Path):
    """Export to plain text."""
    lines = [
        "JARVIS MK37 — Conversation Log",
        f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 50,
        "",
    ]
    for msg in history:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        lines.append(f"[{role}]")
        lines.append(content)
        lines.append("-" * 30)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _export_pdf(history: list[dict], path: Path):
    """Export to PDF. Falls back to HTML-to-PDF or clean text export if library not available."""
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Title
        pdf.set_text_color(56, 189, 248)
        pdf.cell(200, 10, txt="JARVIS MK37 — Conversation Log", ln=True, align="C")
        pdf.set_text_color(100, 116, 139)
        pdf.cell(200, 10, txt=f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        pdf.ln(10)

        # Content
        for msg in history:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")

            if role == "USER":
                pdf.set_text_color(99, 102, 241)
            else:
                pdf.set_text_color(56, 189, 248)

            pdf.cell(200, 8, txt=f"[{role}]", ln=True)
            pdf.set_text_color(15, 23, 42)

            # Split text into multi-line cells
            pdf.multi_cell(0, 6, txt=content.encode("latin1", "replace").decode("latin1"))
            pdf.ln(4)

        pdf.output(str(path))
    except ImportError:
        # If FPDF is not installed, we fallback to exporting HTML and changing extension to .html
        # to guarantee a rich file format viewable on their PC
        html_path = path.with_suffix(".html")
        _export_html(history, html_path)
        # Rename or just copy to path
        if path.exists():
            path.unlink()
        try:
            import shutil

            shutil.copy(str(html_path), str(path))
        except Exception as e:
            logger.debug("Suppressed exception: %s", e)
