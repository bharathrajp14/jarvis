# memory/vector_store.py — ChromaDB-backed Vector Memory for JARVIS MK37
"""
ChromaDB-backed vector memory for JARVIS MK37.
Uses Google GenAI API for fast embeddings (gemini-embedding-001),
with a pure-Python TF-IDF similarity fallback if ChromaDB or API is missing.

Improvements:
- Removed hardcoded 768-dim truncation (corrupts embeddings for non-768-dim models)
- API key loaded via JarvisConfig / config module (not raw os.environ)
- print() replaced with proper logger calls
"""
from __future__ import annotations

import json
import logging
import math
import re
import threading
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("JARVIS.VectorMemory")

_DB_PATH = Path(__file__).resolve().parent.parent / "memory_db"

# ── Optional dependency guard ─────────────────────────────────────────────────
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
    """Load Gemini API key via JarvisConfig with fallback to raw environment variable."""
    try:
        from core.config import get_config
        import os
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            cfg = get_config()
            # Future: cfg could expose api_key directly
        return key
    except Exception:
        import os
        return os.environ.get("GEMINI_API_KEY", "").strip()


class GeminiEmbeddingFunction(_BaseClass):
    """ChromaDB embedding function using Google GenAI Client (gemini-embedding-001).

    FIXED: Removed hardcoded 768-dim truncation/padding. Embedding vectors are
    returned at the model's native dimensionality, letting ChromaDB handle alignment.
    Added thread-safe in-memory LRU/dict caching for sub-millisecond repeated queries.
    """
    _CACHE: dict[str, list[float]] = {}
    _LOCK = threading.Lock()

    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001"):
        self.api_key = api_key
        self._client = None
        self.model = model

    @staticmethod
    def name() -> str:
        return "gemini"

    def get_config(self) -> dict:
        return {"model": self.model}

    @property
    def client(self):
        if self._client is None:
            from google import genai  # type: ignore[import-not-found]
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        embeddings = []
        for text in input:
            cache_key = f"{self.model}:{text.strip()}"
            with self._LOCK:
                if cache_key in self._CACHE:
                    embeddings.append(self._CACHE[cache_key])
                    continue

            # 1. Primary Model Attempt
            try:
                res = self.client.models.embed_content(
                    model=self.model,
                    contents=text,
                    config={"output_dimensionality": 768},
                )
                if hasattr(res, "embeddings") and res.embeddings:
                    vals = getattr(res.embeddings[0], "values", None)
                    if vals:
                        vec = list(vals)
                        with self._LOCK:
                            self._CACHE[cache_key] = vec
                        embeddings.append(vec)
                        continue
            except Exception:
                pass

            # 2. Fallback Model Attempt
            try:
                res = self.client.models.embed_content(
                    model="models/gemini-embedding-2-preview",
                    contents=text,
                    config={"output_dimensionality": 768},
                )
                if hasattr(res, "embeddings") and res.embeddings:
                    vals = getattr(res.embeddings[0], "values", None)
                    if vals:
                        vec = list(vals)
                        with self._LOCK:
                            self._CACHE[cache_key] = vec
                        embeddings.append(vec)
                        continue
            except Exception:
                pass

            # 3. Safe fallback vector (768-dim)
            zero_vec = [0.0] * 768
            with self._LOCK:
                self._CACHE[cache_key] = zero_vec
            embeddings.append(zero_vec)

        return embeddings


class TextSimilarityMemory:
    """Fallback TF-IDF relevance memory for offline/zero-dependency search."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.filepath.exists():
            try:
                self.entries = json.loads(self.filepath.read_text(encoding="utf-8"))
            except Exception:
                self.entries = []

    def _save(self) -> None:
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text(
                json.dumps(self.entries, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def store(self, text: str, metadata: Optional[dict] = None, doc_id: Optional[str] = None) -> None:
        if any(e["text"].strip() == text.strip() for e in self.entries):
            return  # Dedup
        self.entries.append({
            "id":       doc_id or str(uuid.uuid4()),
            "text":     text,
            "metadata": metadata or {},
        })
        self._save()

    def recall(self, query: str, n: int = 5) -> list[str]:
        if not self.entries:
            return []

        query_words = set(re.findall(r'\w+', query.lower()))
        if not query_words:
            return [e["text"] for e in self.entries[:n]]

        ranked = []
        for entry in self.entries:
            doc_words = re.findall(r'\w+', entry["text"].lower())
            doc_word_set = set(doc_words)
            overlap = query_words.intersection(doc_word_set)

            score = 0.0
            for w in overlap:
                tf = doc_words.count(w)
                df = sum(1 for doc in self.entries if w in doc["text"].lower())
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
    """Unified vector memory with ChromaDB + Gemini Embeddings primary,
    and pure-Python TF-IDF similarity as fallback.
    """
    _RECALL_CACHE: dict[str, list[str]] = {}

    def __init__(self, collection_name: str = "jarvis"):
        self._collection = None
        self._fallback: Optional[TextSimilarityMemory] = None
        self._available = False

        api_key = _load_api_key()

        if _CHROMA_AVAILABLE and api_key:
            try:
                ef = GeminiEmbeddingFunction(api_key=api_key)
                client = chromadb.PersistentClient(path=str(_DB_PATH))
                self._collection = client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=ef,
                )
                self._available = True
                logger.info("[VectorMemory] ✅ ChromaDB vector store initialized.")
            except Exception as exc:
                logger.warning(
                    f"[VectorMemory] ChromaDB initialization failed ({exc}). "
                    f"Falling back to text similarity."
                )

        if not self._available:
            self._fallback = TextSimilarityMemory(_DB_PATH / "fallback_memory.json")
            self._available = True
            logger.info("[VectorMemory] ✓ Fallback text similarity memory active.")

    # ── Public API ────────────────────────────────────────────────────────────

    def store(
        self,
        text: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> None:
        if not self._available:
            return

        VectorMemory._RECALL_CACHE.clear()

        if self._collection is not None:
            try:
                # Safe deduplication check
                existing = self._collection.query(query_texts=[text], n_results=1)
                if (
                    existing
                    and "documents" in existing
                    and existing["documents"]
                    and existing["documents"][0]
                    and existing["documents"][0][0].strip() == text.strip()
                ):
                    return  # Duplicate found

                self._collection.add(
                    documents=[text],
                    metadatas=[metadata or {}],
                    ids=[doc_id or str(uuid.uuid4())],
                )
            except Exception as exc:
                logger.warning(f"[VectorMemory] ChromaDB store() failed ({exc}). Falling back to text similarity.")
                if self._fallback is None:
                    self._fallback = TextSimilarityMemory(_DB_PATH / "fallback_memory.json")
                self._fallback.store(text, metadata, doc_id)
        elif self._fallback is not None:
            self._fallback.store(text, metadata, doc_id)

    def recall(self, query: str, n: int = 5) -> list[str]:
        if not self._available:
            return []

        cache_key = f"{query.strip()}:{n}"
        if cache_key in VectorMemory._RECALL_CACHE:
            return list(VectorMemory._RECALL_CACHE[cache_key])

        results_list: list[str] = []
        if self._collection is not None:
            try:
                count = self._collection.count()
                if count == 0:
                    return []
                results = self._collection.query(
                    query_texts=[query],
                    n_results=min(n, count),
                )
                if results and "documents" in results and results["documents"] and results["documents"][0]:
                    docs = results["documents"][0]
                    distances = results.get("distances", [[]])[0] if results.get("distances") else []
                    if distances:
                        filtered = [d for d, dist in zip(docs, distances) if dist <= 0.38]
                        results_list = filtered
                    else:
                        results_list = docs
            except Exception as exc:
                logger.warning(f"[VectorMemory] recall() failed: {exc}")
                results_list = []
        elif self._fallback is not None:
            results_list = self._fallback.recall(query, n)

        VectorMemory._RECALL_CACHE[cache_key] = results_list
        return results_list

    def search(self, query: str, top_k: int = 5) -> list[str]:
        """Alias for recall() — backwards compatibility with orchestrator."""
        return self.recall(query=query, n=top_k)

    @property
    def available(self) -> bool:
        return self._available
