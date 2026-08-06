# history/linker.py — Semantic Session Linker for JARVIS MK37
"""
Semantic session linker using ChromaDB or TF-IDF fallback.

On session close, the session summary is embedded into a vector store.
This allows finding semantically related past sessions and injecting
their context into the current working memory.

Features:
  - ChromaDB with Gemini text-embedding-004
  - Pure-Python TF-IDF similarity fallback when ChromaDB is unavailable
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any


_DB_DIR = Path.home() / ".jarvis" / "history"
_COLLECTION_NAME = "session_links"

_chroma_available = False
try:
    import chromadb
    _chroma_available = True
except ImportError:
    pass


class HistoryLinker:
    """Builds semantic links between JARVIS sessions using embeddings or text similarity."""

    def __init__(self) -> None:
        self._collection: Any = None
        self._fallback_file = _DB_DIR / "fallback_session_links.json"
        self._fallback_entries: list[dict] = []

        if _chroma_available:
            try:
                db_path = str(_DB_DIR / ".chromadb_sessions")
                client = chromadb.PersistentClient(path=db_path)
                self._collection = client.get_or_create_collection(
                    name=_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        if not self.available:
            self._load_fallback()

    @property
    def available(self) -> bool:
        return self._collection is not None

    def _load_fallback(self):
        if self._fallback_file.exists():
            try:
                self._fallback_entries = json.loads(self._fallback_file.read_text(encoding="utf-8"))
            except Exception:
                self._fallback_entries = []

    def _save_fallback(self):
        try:
            self._fallback_file.parent.mkdir(parents=True, exist_ok=True)
            self._fallback_file.write_text(json.dumps(self._fallback_entries, indent=2), encoding="utf-8")
        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.debug('Suppressed exception: %s', e)
            else:
                import logging
                logging.getLogger(__name__).debug('Suppressed exception: %s', e)
    def on_session_close(self, session_id: str, summary: str, mode: str = "", backend: str = "") -> None:
        """Embed a session summary into the vector store on close."""
        if not summary or not summary.strip():
            return
        
        if self.available:
            try:
                self._collection.upsert(
                    ids=[session_id],
                    documents=[summary],
                    metadatas=[{"mode": mode, "backend": backend}],
                )
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        else:
            # Fallback storage
            self._fallback_entries = [e for e in self._fallback_entries if e["session_id"] != session_id]
            self._fallback_entries.append({
                "session_id": session_id,
                "summary": summary,
                "mode": mode,
                "backend": backend,
            })
            self._save_fallback()

    def find_related(self, session_id: str, n: int = 5) -> list[dict]:
        """Find sessions semantically related to the given session.

        Returns a list of dicts with keys: session_id, similarity, mode, backend.
        """
        if self.available:
            try:
                result = self._collection.get(ids=[session_id], include=["documents"])
                if not result or not result["documents"] or not result["documents"][0]:
                    return []
                query_text = result["documents"][0]

                count = self._collection.count()
                if count <= 1:
                    return []

                search = self._collection.query(
                    query_texts=[query_text],
                    n_results=min(n + 1, count),
                    include=["metadatas", "distances"],
                )

                if not search or not search["ids"] or not search["ids"][0]:
                    return []

                results = []
                for i, sid in enumerate(search["ids"][0]):
                    if sid == session_id:
                        continue
                    dist = search["distances"][0][i] if search["distances"] else 0
                    meta = search["metadatas"][0][i] if search["metadatas"] else {}
                    results.append({
                        "session_id": sid,
                        "similarity": round(max(0.0, 1.0 - dist), 3),
                        "mode": meta.get("mode", ""),
                        "backend": meta.get("backend", ""),
                    })

                return results[:n]
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.warning(f"{ f"[HistoryLinker] Search error: {e}" }" if isinstance(f"[HistoryLinker] Search error: {e}", str) else f"[HistoryLinker] Search error: {e}")
                else:
                    import logging
                    logging.getLogger(__name__).warning(f"{ f"[HistoryLinker] Search error: {e}" }" if isinstance(f"[HistoryLinker] Search error: {e}", str) else f"[HistoryLinker] Search error: {e}")
                return []
        else:
            # TF-IDF Fallback search
            current = next((e for e in self._fallback_entries if e["session_id"] == session_id), None)
            if not current:
                return []
            
            q_words = set(re.findall(r'\w+', current["summary"].lower()))
            if not q_words:
                return []

            ranked = []
            for e in self._fallback_entries:
                if e["session_id"] == session_id:
                    continue
                d_words = re.findall(r'\w+', e["summary"].lower())
                overlap = q_words.intersection(set(d_words))
                if overlap:
                    sim = len(overlap) / float(len(q_words | set(d_words)))
                    ranked.append((sim, {
                        "session_id": e["session_id"],
                        "similarity": round(sim, 3),
                        "mode": e.get("mode", ""),
                        "backend": e.get("backend", ""),
                    }))
            
            ranked.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in ranked[:n]]

    def inject_context(self, session_id: str, working_memory: Any) -> int:
        """Inject top-3 related session summaries as context blocks into working memory."""
        related = self.find_related(session_id, n=3)
        if not related:
            return 0

        injected = 0
        for rel in related:
            try:
                summary = ""
                if self.available:
                    result = self._collection.get(ids=[rel["session_id"]], include=["documents"])
                    if result and result["documents"] and result["documents"][0]:
                        summary = result["documents"][0]
                else:
                    item = next((e for e in self._fallback_entries if e["session_id"] == rel["session_id"]), None)
                    if item:
                        summary = item["summary"]

                if summary:
                    context_block = (
                        f"[Related Session Context (similarity: {rel['similarity']:.2f})]:\n"
                        f"{summary[:500]}"
                    )
                    working_memory.add("user", context_block)
                    injected += 1
            except Exception:
                continue

        return injected
