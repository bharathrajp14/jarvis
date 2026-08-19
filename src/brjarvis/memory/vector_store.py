# memory/vector_store.py - ChromaDB-backed Vector Memory for JARVIS
"""
ChromaDB-backed vector memory for BR JARVIS.

CRITICAL FIX (Phase 2 - Forensic Audit):
  The previous search() returned score=0.85 hardcoded with empty metadata.
  This version:
  1. Stores memory_id in ChromaDB document metadata on every index_memory() call.
  2. Returns real cosine similarity scores from ChromaDB (1.0 - distance/2.0).
  3. Returns real normalized TF-IDF scores from the fallback.
  4. Exposes a SearchResult namedtuple with memory_id, text, score, metadata.
  5. Semantic candidates can now enter retrieval pool independently.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import uuid
from collections import namedtuple
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.VectorMemory")

_DB_PATH = paths.MEMORY_ROOT

_CHROMA_AVAILABLE = False

try:
    import chromadb  # type: ignore
    _CHROMA_AVAILABLE = True
except ImportError:
    pass


# ── Structured Search Result ──────────────────────────────────────────────────

class SearchResult:
    """Structured result from VectorMemory.search() supporting attribute, tuple, and dict access."""
    __slots__ = ("memory_id", "text", "score", "metadata")

    def __init__(
        self,
        memory_id: str = "",
        text: str = "",
        score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.memory_id = memory_id
        self.text = text
        self.score = score
        self.metadata = metadata or {}

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            if item == "memory_id":
                return self.memory_id
            elif item == "text":
                return self.text
            elif item == "score":
                return self.score
            elif item == "metadata":
                return self.metadata
            raise KeyError(item)
        elif isinstance(item, int):
            return (self.memory_id, self.text, self.score, self.metadata)[item]
        raise TypeError(f"Invalid index type: {type(item)}")

    def __len__(self) -> int:
        return 4

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"SearchResult(memory_id={self.memory_id!r}, text={self.text!r}, score={self.score!r}, metadata={self.metadata!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SearchResult):
            return (self.memory_id, self.text, self.score, self.metadata) == (
                other.memory_id, other.text, other.score, other.metadata
            )
        if isinstance(other, dict):
            return self.to_dict() == other
        return False


def _load_api_key() -> str:
    """Load Gemini API key via environment or configuration."""
    key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        try:
            config_path = paths.CONFIG_ROOT / "api_keys.json"
            if config_path.exists():
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                key = cfg.get("gemini_api_key", "").strip()
        except Exception:
            pass
    return key


# ── TF-IDF Fallback ───────────────────────────────────────────────────────────

class TextSimilarityMemory:
    """Pure-Python TF-IDF similarity fallback when ChromaDB is unavailable.

    FIXED: Returns real normalized TF-IDF scores and preserves memory_id.
    """

    def __init__(self, json_path: Path):
        self.path = Path(json_path)
        self.entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.entries = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("[VectorMemory] Failed to load fallback JSON: %s", e)
                self.entries = []

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.entries, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("[VectorMemory] Failed to save fallback JSON: %s", e)

    def store(self, text: str, metadata: Optional[dict] = None, doc_id: Optional[str] = None) -> None:
        """Store a document. Metadata MUST include memory_id when linking to CanonicalMemory."""
        clean_text = text.strip()
        if not clean_text:
            return
        resolved_id = doc_id or (metadata or {}).get("memory_id") or str(uuid.uuid4())
        for i, e in enumerate(self.entries):
            if e.get("id") == resolved_id:
                self.entries[i] = {"id": resolved_id, "text": clean_text, "metadata": metadata or {}}
                self._save()
                return
        self.entries.append({"id": resolved_id, "text": clean_text, "metadata": metadata or {}})
        self._save()

    def search(self, query: str, n: int = 5) -> List[SearchResult]:
        """Return up to n SearchResults with normalized TF-IDF scores."""
        if not self.entries:
            return []
        query_words = re.findall(r"\w+", query.lower())
        if not query_words:
            return [
                SearchResult(
                    memory_id=e.get("metadata", {}).get("memory_id", e.get("id", "")),
                    text=e.get("text", ""),
                    score=0.01,
                    metadata=e.get("metadata", {}),
                )
                for e in self.entries[:n]
            ]
        query_word_set = set(query_words)
        scored: list[tuple[float, dict]] = []
        for entry in self.entries:
            doc_text = entry.get("text", "")
            doc_words = re.findall(r"\w+", doc_text.lower())
            doc_word_set = set(doc_words)
            overlap = query_word_set.intersection(doc_word_set)
            raw_score = 0.0
            for w in overlap:
                tf = doc_words.count(w)
                df = sum(1 for doc in self.entries if w in doc.get("text", "").lower())
                idf = math.log((1 + len(self.entries)) / (1 + df)) + 1.0
                raw_score += math.log(1 + tf) * idf
            if raw_score > 0:
                scored.append((raw_score, entry))
        if not scored:
            return []
        max_score = max(s for s, _ in scored)
        results = []
        for raw_score, entry in sorted(scored, key=lambda x: x[0], reverse=True)[:n]:
            norm_score = raw_score / max_score if max_score > 0 else 0.0
            meta = entry.get("metadata", {})
            results.append(SearchResult(
                memory_id=meta.get("memory_id", entry.get("id", "")),
                text=entry.get("text", ""),
                score=round(norm_score, 4),
                metadata=meta,
            ))
        return results

    def recall(self, query: str, n: int = 5) -> list[str]:
        """Legacy text-only interface."""
        return [r.text for r in self.search(query, n)]

    def delete(self, doc_id: str) -> bool:
        """Remove an entry by ID."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.get("id") != doc_id]
        if len(self.entries) < before:
            self._save()
            return True
        return False


# ── Main VectorMemory Class ───────────────────────────────────────────────────

class VectorMemory:
    """Unified vector memory with ChromaDB primary and TF-IDF fallback.

    Phase 2 fixes:
    - search() returns real cosine similarity from ChromaDB (1.0 - dist/2.0)
    - metadata (including memory_id) preserved through full pipeline
    - TF-IDF fallback returns normalized 0.0-1.0 scores
    - index_memory() ensures memory_id is stored in metadata
    """

    def __init__(self, collection_name: str = "jarvis", persist_dir: Optional[str] = None):
        self._collection = None
        self._fallback: Optional[TextSimilarityMemory] = None
        self._available = False
        self._collection_name = collection_name
        self.persist_dir = Path(persist_dir) if persist_dir else _DB_PATH
        self._cache_lock = threading.Lock()
        self._recall_cache: dict[str, list[str]] = {}
        self._search_cache: dict[str, list] = {}

        api_key = _load_api_key()

        if _CHROMA_AVAILABLE and api_key:
            try:
                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                self._collection = self._client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                self._available = True
                logger.info("[VectorMemory] ChromaDB vector store initialized.")
            except Exception as exc:
                logger.warning("[VectorMemory] ChromaDB init notice (%s). Using TF-IDF fallback.", exc)

        if not self._available:
            self._fallback = TextSimilarityMemory(self.persist_dir / "fallback_memory.json")
            self._available = True
            logger.info("[VectorMemory] TF-IDF fallback memory active.")

    def _invalidate_cache(self) -> None:
        with self._cache_lock:
            self._recall_cache.clear()
            self._search_cache.clear()

    def index_memory(self, memory_id: str, content: str, extra_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Index a CanonicalMemory. Preferred over store() for canonical memory linking."""
        meta: Dict[str, Any] = {"memory_id": memory_id}
        if extra_metadata:
            meta.update(extra_metadata)
        self.store(text=content, metadata=meta, doc_id=memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        """Remove a canonical memory from the vector index."""
        removed = False
        if self._collection is not None:
            try:
                self._collection.delete(ids=[memory_id])
                removed = True
            except Exception as exc:
                logger.debug("[VectorMemory] ChromaDB delete notice: %s", exc)
        if self._fallback is not None:
            if self._fallback.delete(memory_id):
                removed = True
        if removed:
            self._invalidate_cache()
        return removed

    def store(self, text: str, metadata: Optional[dict] = None, doc_id: Optional[str] = None) -> None:
        """Store a text snippet with metadata."""
        if not self._available or not text:
            return
        self._invalidate_cache()
        resolved_id = doc_id or (metadata or {}).get("memory_id") or str(uuid.uuid4())
        if self._collection is not None:
            try:
                self._collection.upsert(
                    documents=[text],
                    metadatas=[metadata or {}],
                    ids=[resolved_id],
                )
                return
            except Exception as exc:
                if "dimension" in str(exc).lower() and hasattr(self, "_client") and self._client:
                    try:
                        self._client.delete_collection(self._collection_name)
                        self._collection = self._client.get_or_create_collection(
                            name=self._collection_name,
                            metadata={"hnsw:space": "cosine"},
                        )
                        self._collection.upsert(documents=[text], metadatas=[metadata or {}], ids=[resolved_id])
                        return
                    except Exception:
                        pass
                logger.debug("[VectorMemory] ChromaDB store() note: %s", exc)
                if self._fallback is None:
                    self._fallback = TextSimilarityMemory(self.persist_dir / "fallback_memory.json")
                self._fallback.store(text, metadata, resolved_id)
        elif self._fallback is not None:
            self._fallback.store(text, metadata, resolved_id)

    def add_memory(self, text: str, metadata: Optional[dict] = None, doc_id: Optional[str] = None) -> None:
        """Alias for store()."""
        self.store(text, metadata, doc_id)

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Search and return SearchResults with REAL similarity scores.

        ChromaDB: similarity = max(0, 1.0 - distance/2.0)  range [0.0, 1.0]
        Fallback: normalized TF-IDF score                   range [0.0, 1.0]
        """
        if not self._available or not query.strip():
            return []

        cache_key = f"search:{query.strip()}:{top_k}"
        with self._cache_lock:
            cached = self._search_cache.get(cache_key)
            if cached is not None:
                return list(cached)

        results: List[SearchResult] = []

        if self._collection is not None:
            try:
                count = self._collection.count()
                if count > 0:
                    raw = self._collection.query(
                        query_texts=[query],
                        n_results=min(top_k, count),
                        include=["documents", "distances", "metadatas"],
                    )
                    docs = (raw.get("documents") or [[]])[0]
                    dists = (raw.get("distances") or [[]])[0]
                    metas = (raw.get("metadatas") or [[]])[0]
                    for i, doc in enumerate(docs):
                        dist = dists[i] if i < len(dists) else 1.0
                        similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                        meta = metas[i] if i < len(metas) else {}
                        memory_id = (meta or {}).get("memory_id", "")
                        results.append(SearchResult(
                            memory_id=memory_id,
                            text=doc,
                            score=round(similarity, 4),
                            metadata=meta or {},
                        ))
            except Exception as exc:
                logger.debug("[VectorMemory] ChromaDB search() note: %s", exc)
                results = []

        if not results and self._fallback is not None:
            results = self._fallback.search(query, top_k)

        results = sorted(results, key=lambda r: r.score, reverse=True)
        with self._cache_lock:
            self._search_cache[cache_key] = results
        return results

    def recall(self, query: str, n: int = 5) -> list[str]:
        """Legacy text-only recall. Use search() for structured results."""
        if not self._available:
            return []
        cache_key = f"recall:{query.strip()}:{n}"
        with self._cache_lock:
            cached = self._recall_cache.get(cache_key)
            if cached is not None:
                return list(cached)
        results = self.search(query, top_k=n)
        text_list = [r.text for r in results]
        with self._cache_lock:
            self._recall_cache[cache_key] = text_list
        return text_list

    @property
    def available(self) -> bool:
        return self._available
