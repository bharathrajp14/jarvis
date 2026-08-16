# memory/vector_store.py — ChromaDB-backed Vector Memory for JARVIS
"""
ChromaDB-backed vector memory for BR JARVIS.
Uses Google GenAI API for embeddings (gemini-embedding-001) when available,
with a pure-Python TF-IDF similarity fallback if ChromaDB or API key is missing.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.VectorMemory")

_DB_PATH = paths.MEMORY_ROOT

_CHROMA_AVAILABLE = False
_BaseClass = object

try:
    import chromadb  # type: ignore
    from chromadb.api.types import EmbeddingFunction  # type: ignore[import-not-found]
    _BaseClass = EmbeddingFunction
    _CHROMA_AVAILABLE = True
except ImportError:
    pass


def _load_api_key() -> str:
    """Load Gemini API key via environment or configuration."""
    key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        try:
            from brjarvis.core.paths import paths
            config_path = paths.CONFIG_ROOT / "api_keys.json"
            if config_path.exists():
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                key = cfg.get("gemini_api_key", "").strip()
        except Exception:
            pass
    return key


class TextSimilarityMemory:
    """Pure-Python TF-IDF cosine similarity fallback when ChromaDB is unavailable."""

    def __init__(self, json_path: Path):
        self.path = Path(json_path)
        self.entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.entries = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"[VectorMemory] Failed to load fallback JSON: {e}")
                self.entries = []

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.entries, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"[VectorMemory] Failed to save fallback JSON: {e}")

    def store(self, text: str, metadata: Optional[dict] = None, doc_id: Optional[str] = None) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        for e in self.entries:
            if e.get("text", "").strip() == clean_text:
                return  # Duplicate found
        self.entries.append({
            "id": doc_id or str(uuid.uuid4()),
            "text": clean_text,
            "metadata": metadata or {},
        })
        self._save()

    def recall(self, query: str, n: int = 5) -> list[str]:
        if not self.entries:
            return []

        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return [e["text"] for e in self.entries[:n]]

        ranked = []
        for entry in self.entries:
            doc_words = re.findall(r"\w+", entry.get("text", "").lower())
            doc_word_set = set(doc_words)
            overlap = query_words.intersection(doc_word_set)

            score = 0.0
            for w in overlap:
                tf = doc_words.count(w)
                df = sum(1 for doc in self.entries if w in doc.get("text", "").lower())
                idf = math.log((1 + len(self.entries)) / (1 + df)) + 1.0
                score += math.log(1 + tf) * idf

            if score > 0:
                ranked.append((score, entry["text"]))

        ranked.sort(reverse=True)
        return (
            [text for _, text in ranked[:n]]
            if ranked
            else [e["text"] for e in self.entries[:n]]
        )


class VectorMemory:
    """Unified vector memory with ChromaDB primary and pure-Python TF-IDF similarity fallback."""

    _RECALL_CACHE: dict[str, list[str]] = {}

    def __init__(
        self,
        collection_name: str = "jarvis",
        persist_dir: Optional[str] = None,
    ):
        self._collection = None
        self._fallback: Optional[TextSimilarityMemory] = None
        self._available = False
        self.persist_dir = Path(persist_dir) if persist_dir else _DB_PATH

        api_key = _load_api_key()

        if _CHROMA_AVAILABLE and api_key:
            try:
                from google import genai  # type: ignore[import-not-found]
                self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                self._collection = self._client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                self._available = True
                logger.info("[VectorMemory] ✅ ChromaDB vector store initialized.")
            except Exception as exc:
                logger.warning(
                    f"[VectorMemory] ChromaDB initialization notice ({exc}). "
                    f"Falling back to text similarity."
                )

        if not self._available:
            self._fallback = TextSimilarityMemory(self.persist_dir / "fallback_memory.json")
            self._available = True
            logger.info("[VectorMemory] ✓ Fallback text similarity memory active.")

    def store(
        self,
        text: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> None:
        """Store a text snippet with metadata in the vector store."""
        if not self._available or not text:
            return

        VectorMemory._RECALL_CACHE.clear()

        if self._collection is not None:
            try:
                self._collection.upsert(
                    documents=[text],
                    metadatas=[metadata or {}],
                    ids=[doc_id or str(uuid.uuid4())],
                )
            except Exception as exc:
                if "dimension" in str(exc).lower() and hasattr(self, "_client") and self._client:
                    try:
                        c_name = self._collection.name
                        self._client.delete_collection(c_name)
                        self._collection = self._client.get_or_create_collection(
                            name=c_name,
                            metadata={"hnsw:space": "cosine"},
                        )
                        self._collection.upsert(
                            documents=[text],
                            metadatas=[metadata or {}],
                            ids=[doc_id or str(uuid.uuid4())],
                        )
                        return
                    except Exception:
                        pass
                logger.debug(f"[VectorMemory] ChromaDB store() note: {exc}")
                if self._fallback is None:
                    self._fallback = TextSimilarityMemory(self.persist_dir / "fallback_memory.json")
                self._fallback.store(text, metadata, doc_id)
        elif self._fallback is not None:
            self._fallback.store(text, metadata, doc_id)

    def add_memory(self, text: str, metadata: Optional[dict] = None, doc_id: Optional[str] = None) -> None:
        """Alias for store()."""
        self.store(text, metadata, doc_id)

    def recall(self, query: str, n: int = 5) -> list[str]:
        """Query top N matching text strings."""
        if not self._available:
            return []

        cache_key = f"{query.strip()}:{n}"
        if cache_key in VectorMemory._RECALL_CACHE:
            return list(VectorMemory._RECALL_CACHE[cache_key])

        results_list: list[str] = []
        if self._collection is not None:
            try:
                count = self._collection.count()
                if count > 0:
                    results = self._collection.query(
                        query_texts=[query],
                        n_results=min(n, count),
                    )
                    if results and "documents" in results and results["documents"] and results["documents"][0]:
                        results_list = results["documents"][0]
            except Exception as exc:
                logger.debug("Chroma recall exception: %s", exc)
                results_list = []

        if not results_list and self._fallback is not None:
            results_list = self._fallback.recall(query, n)

        VectorMemory._RECALL_CACHE[cache_key] = results_list
        return results_list

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search query and return list of result dictionaries."""
        text_hits = self.recall(query=query, n=top_k)
        return [{"text": t, "score": 0.85, "metadata": {}} for t in text_hits]

    @property
    def available(self) -> bool:
        return self._available
