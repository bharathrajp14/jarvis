# history/ — Persistent session history engine for JARVIS MK37.
"""
Provides:
  - SessionStore    — SQLite-backed session and turn storage
  - HistoryLinker   — ChromaDB semantic session linker
  - SessionReplay   — Session reconstruction and export
  - write_audit     — Structured JSON audit writer
"""

from __future__ import annotations

from .audit_writer import write_audit
from .linker import HistoryLinker
from .replay import export_markdown, load_session, replay_as_context
from .session_store import SessionStore

__all__ = [
    "SessionStore",
    "HistoryLinker",
    "load_session",
    "replay_as_context",
    "export_markdown",
    "write_audit",
]
