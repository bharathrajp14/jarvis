# actions/rag_library.py — JARVIS MK37 LocalLibrary RAG Engine
"""
Retrieval-Augmented Generation (RAG) for chatting with personal documents.
Supports: PDF, DOCX, TXT, CSV, Markdown, webpages, and screenshots (via OCR).
Uses ChromaDB for vector storage and semantic search.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Generator


# ── Configuration ─────────────────────────────────────────────────────────────

COLLECTION_NAME = "local_library"
CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 100    # overlap between chunks
MAX_CHUNKS_PER_DOC = 500

import threading

_chroma_client = None
_collection = None
_CHROMA_LOCK = threading.Lock()


def _get_collection():
    """Get or create the ChromaDB collection for the local library."""
    global _chroma_client, _collection
    with _CHROMA_LOCK:
        if _collection is not None:
            return _collection

        try:
            import chromadb
            db_path = os.environ.get("JARVIS_RAG_DB", "memory_db/rag_library")
            Path(db_path).mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=db_path)
            _collection = _chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            return _collection
        except Exception as e:
            print(f"[RAG] Failed to initialize ChromaDB: {e}")
            return None


# ── Text Extraction ───────────────────────────────────────────────────────────

def _extract_text_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n\n".join(text_parts)
    except ImportError:
        # Fallback: try pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            return f"[ERROR: Install PyMuPDF or pdfplumber to read PDFs: pip install PyMuPDF]"


def _extract_text_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except ImportError:
        return "[ERROR: Install python-docx to read DOCX files: pip install python-docx]"


def _extract_text_csv(file_path: str) -> str:
    """Extract text from a CSV file."""
    import csv
    rows = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(" | ".join(row))
    return "\n".join(rows)


def _extract_text_plain(file_path: str) -> str:
    """Extract text from a plain text or Markdown file."""
    return Path(file_path).read_text(encoding="utf-8", errors="replace")


def _extract_text_webpage(url: str) -> str:
    """Fetch and extract text from a webpage."""
    try:
        import requests
        from html.parser import HTMLParser

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts = []
                self._skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = True

            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = False

            def handle_data(self, data):
                if not self._skip:
                    text = data.strip()
                    if text:
                        self.text_parts.append(text)

        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        extractor = _TextExtractor()
        extractor.feed(resp.text)
        return " ".join(extractor.text_parts)
    except Exception as e:
        return f"[ERROR: Failed to fetch webpage: {e}]"


def extract_text(file_path: str) -> str:
    """Extract text from a file based on its extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    extractors = {
        ".pdf": _extract_text_pdf,
        ".docx": _extract_text_docx,
        ".doc": _extract_text_docx,
        ".csv": _extract_text_csv,
        ".txt": _extract_text_plain,
        ".md": _extract_text_plain,
        ".markdown": _extract_text_plain,
        ".rst": _extract_text_plain,
        ".log": _extract_text_plain,
        ".json": _extract_text_plain,
        ".xml": _extract_text_plain,
        ".html": _extract_text_plain,
        ".htm": _extract_text_plain,
    }

    extractor = extractors.get(ext)
    if extractor:
        return extractor(str(path))
    return f"[Unsupported file type: {ext}. Supported: {', '.join(extractors.keys())}]"


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at a sentence boundary
        if end < len(text):
            # Look for sentence end near the chunk boundary
            for sep in ['. ', '.\n', '!\n', '?\n', '\n\n']:
                last_sep = text.rfind(sep, start + chunk_size // 2, end + 50)
                if last_sep > 0:
                    end = last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            if len(chunks) >= MAX_CHUNKS_PER_DOC:
                break

        start = end - overlap

    return chunks


# ── Core RAG Operations ──────────────────────────────────────────────────────

def ingest_file(file_path: str, doc_name: str = None) -> dict:
    """
    Ingest a document into the RAG library.

    Args:
        file_path: Path to the document file.
        doc_name: Optional custom name for the document.

    Returns:
        dict with 'status', 'chunks', 'doc_name'.
    """
    collection = _get_collection()
    if collection is None:
        return {"error": "RAG library not initialized. Is ChromaDB installed?"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    name = doc_name or path.name
    text = extract_text(str(path))
    if text.startswith("[ERROR"):
        return {"error": text}

    chunks = _chunk_text(text)
    if not chunks:
        return {"error": "No text extracted from the document."}

    # Generate unique IDs based on document name + chunk index
    doc_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    ids = [f"{doc_hash}_chunk_{i}" for i in range(len(chunks))]

    # Delete old chunks for this document (re-ingestion)
    try:
        existing = collection.get(where={"doc_name": name})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    # Add chunks with metadata
    metadatas = [
        {
            "doc_name": name,
            "file_path": str(path.resolve()),
            "chunk_index": i,
            "total_chunks": len(chunks),
            "ingested_at": datetime.now().isoformat(),
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "status": "success",
        "doc_name": name,
        "chunks": len(chunks),
        "total_chars": len(text),
    }


def ingest_webpage(url: str, doc_name: str = None) -> dict:
    """Ingest a webpage into the RAG library."""
    collection = _get_collection()
    if collection is None:
        return {"error": "RAG library not initialized."}

    name = doc_name or url.split("//")[-1].split("/")[0]
    text = _extract_text_webpage(url)
    if text.startswith("[ERROR"):
        return {"error": text}

    chunks = _chunk_text(text)
    if not chunks:
        return {"error": "No text extracted from the webpage."}

    doc_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    ids = [f"{doc_hash}_chunk_{i}" for i in range(len(chunks))]

    # Delete old chunks
    try:
        existing = collection.get(where={"doc_name": name})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    metadatas = [
        {
            "doc_name": name,
            "source_url": url,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "ingested_at": datetime.now().isoformat(),
        }
        for i in range(len(chunks))
    ]

    collection.add(ids=ids, documents=chunks, metadatas=metadatas)

    return {"status": "success", "doc_name": name, "chunks": len(chunks)}


def ingest_screenshot(image_bytes: bytes, doc_name: str = None) -> dict:
    """Ingest a screenshot by OCR-ing it with Gemini Vision, then indexing the text."""
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return {"error": "GEMINI_API_KEY not set for OCR."}

        client = genai.Client(api_key=api_key)
        import base64
        b64 = base64.b64encode(image_bytes).decode()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {"text": "Extract ALL text from this screenshot/image. Return only the text content, preserving structure and formatting."},
                {"inline_data": {"mime_type": "image/png", "data": b64}},
            ],
        )
        text = response.text
        if not text:
            return {"error": "No text detected in the screenshot."}

        name = doc_name or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        chunks = _chunk_text(text)
        if not chunks:
            return {"error": "No meaningful text extracted."}

        collection = _get_collection()
        if collection is None:
            return {"error": "RAG library not initialized."}

        doc_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        ids = [f"{doc_hash}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_name": name, "source": "screenshot", "chunk_index": i,
             "total_chunks": len(chunks), "ingested_at": datetime.now().isoformat()}
            for i in range(len(chunks))
        ]
        collection.add(ids=ids, documents=chunks, metadatas=metadatas)

        return {"status": "success", "doc_name": name, "chunks": len(chunks)}
    except Exception as e:
        return {"error": f"Screenshot ingestion failed: {e}"}


def query(question: str, top_k: int = 5, doc_filter: str = None) -> list[dict]:
    """
    Query the RAG library for relevant document chunks.

    Args:
        question: The search query.
        top_k: Number of results to return.
        doc_filter: Optional document name to filter by.

    Returns:
        List of dicts with 'text', 'doc_name', 'score', 'chunk_index'.
    """
    collection = _get_collection()
    if collection is None:
        return []

    kwargs = {"query_texts": [question], "n_results": top_k}
    if doc_filter:
        kwargs["where"] = {"doc_name": doc_filter}

    try:
        results = collection.query(**kwargs)
    except Exception as e:
        print(f"[RAG] Query error: {e}")
        return []

    output = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0
            output.append({
                "text": doc,
                "doc_name": meta.get("doc_name", "unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "score": round(1 - distance, 4),  # Convert distance to similarity
                "source": meta.get("file_path", meta.get("source_url", "")),
            })

    return output


def list_documents() -> list[dict]:
    """List all documents in the RAG library."""
    collection = _get_collection()
    if collection is None:
        return []

    try:
        all_data = collection.get()
        if not all_data or not all_data["metadatas"]:
            return []

        docs = {}
        for meta in all_data["metadatas"]:
            name = meta.get("doc_name", "unknown")
            if name not in docs:
                docs[name] = {
                    "doc_name": name,
                    "chunks": 0,
                    "ingested_at": meta.get("ingested_at", ""),
                    "source": meta.get("file_path", meta.get("source_url", "")),
                }
            docs[name]["chunks"] += 1

        return list(docs.values())
    except Exception as e:
        print(f"[RAG] List error: {e}")
        return []


def delete_document(doc_name: str) -> dict:
    """Delete a document from the RAG library."""
    collection = _get_collection()
    if collection is None:
        return {"error": "RAG library not initialized."}

    try:
        existing = collection.get(where={"doc_name": doc_name})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
            return {"status": "deleted", "doc_name": doc_name, "chunks_removed": len(existing["ids"])}
        return {"error": f"Document '{doc_name}' not found."}
    except Exception as e:
        return {"error": f"Delete failed: {e}"}


def rag_chat(question: str, top_k: int = 5, doc_filter: str = None) -> str:
    """
    RAG-augmented chat: retrieve relevant chunks and generate an answer.
    Uses the default LLM backend to answer based on retrieved context.
    """
    results = query(question, top_k=top_k, doc_filter=doc_filter)

    if not results:
        return f"No relevant information found in the library for: '{question}'"

    # Build context from retrieved chunks
    context_parts = []
    for r in results:
        context_parts.append(
            f"[Source: {r['doc_name']}, Chunk {r['chunk_index']}, "
            f"Relevance: {r['score']:.0%}]\n{r['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Generate answer using the default backend
    try:
        from core.bootstrap import build_assistant_runtime
        runtime = build_assistant_runtime()
        router = runtime.router

        system = (
            "You are a helpful assistant answering questions based on the user's "
            "personal document library. Use ONLY the provided context to answer. "
            "If the context doesn't contain enough information, say so. "
            "Always cite which document the information comes from."
        )
        messages = [
            {"role": "user", "content": f"Context from my documents:\n\n{context}\n\n"
                                         f"Question: {question}"}
        ]
        return router.run(router.default, messages, system)
    except Exception as e:
        # Return raw context if LLM fails
        return f"Retrieved context (LLM unavailable):\n\n{context}"


# ── 3D Knowledge Galaxy & Markdown Scanner ───────────────────────────────────

def ensure_sample_notes(notes_dir: Path):
    """Generate 25 sample markdown notes if notes directory is empty or missing."""
    notes_dir.mkdir(parents=True, exist_ok=True)
    if list(notes_dir.glob("*.md")):
        return

    sample_topics = [
        ("Quantum Computing Core", "overview", "Quantum computing leverages qubits to process multidimensional data. Linked to [[AI Synergy]] and [[Hardware Roadmap]]."),
        ("AI Synergy", "ai", "Synergy between neural architectures and symbolic reasoning. Refers to [[Quantum Computing Core]]."),
        ("Hardware Roadmap", "hardware", "Next-gen GPU and TPU clusters. Dependent on [[Quantum Computing Core]] cooling solutions."),
        ("Neural TTS Engine", "voice", "Acoustic modeling using Tacotron2 and WaveGlow. Integrates with [[Voice Assistant Protocol]]."),
        ("Voice Assistant Protocol", "voice", "Low-latency streaming over WebSockets. Drives [[Neural TTS Engine]] and [[JARVIS Cyberpunk HUD]]."),
        ("JARVIS Cyberpunk HUD", "ui", "PySide6 visual interface with Iron Man reactor pulse. Connects to [[Voice Assistant Protocol]]."),
        ("ChromaDB Vector Store", "memory", "High-performance embedding storage for document RAG. Used by [[Memory Manager 2.0]]."),
        ("Memory Manager 2.0", "memory", "Hierarchical episodic and semantic memory. Integrates [[ChromaDB Vector Store]] and [[Long Term Storage]]."),
        ("Long Term Storage", "memory", "Persistent JSON store for user preferences and history. Managed by [[Memory Manager 2.0]]."),
        ("Gemini Pro Integration", "models", "Primary reasoning backend for complex agentic workflows. Synergizes with [[Router Strategy]]."),
        ("Router Strategy", "router", "Adaptive model switching between local and cloud LLMs. Routes tasks to [[Gemini Pro Integration]]."),
        ("Task Queue Execution", "agent", "Asynchronous priority queue worker system. Dispatches sub-tasks to [[Agent Executor]]."),
        ("Agent Executor", "agent", "Step planner and tool registry invocation engine. Triggered by [[Task Queue Execution]]."),
        ("Security Sentinel", "security", "JWT authentication and permission gatekeeper. Secures endpoints for [[FastAPI Gateway]]."),
        ("FastAPI Gateway", "server", "Async REST and WebSocket server for dashboard and HUD. Protected by [[Security Sentinel]]."),
        ("Proactive Monitor", "proactive", "Background watcher scanning OS events and system telemetry. Alerts [[JARVIS Cyberpunk HUD]]."),
        ("QR Mobile Dashboard", "ui", "PWA dashboard accessible via mobile QR code scan. Connects to [[FastAPI Gateway]]."),
        ("Universal File Processor", "tools", "Extracts text from PDF, DOCX, CSV, and OCR images. Feeds [[ChromaDB Vector Store]]."),
        ("Live OS Control", "actions", "Controls native Windows applications and window management. Utilized by [[Agent Executor]]."),
        ("Web Research RAG", "actions", "Scrapes web pages and synthesizes live search cards. Feeds data into [[ChromaDB Vector Store]]."),
        ("Deep Audit Test Suite", "testing", "Self-healing test runner ensuring 100% code coverage. Tests [[FastAPI Gateway]]."),
        ("British Butler Persona", "personality", "Witty, dry, impeccably polite persona addressing user as sir. Customizes [[Gemini Pro Integration]]."),
        ("Total Recall Protocol", "voice", "Voice capture starting with 'remember that'. Appends notes to [[Captures Vault]]."),
        ("Captures Vault", "notes", "Dynamic storage folder for voice and chat captures. Managed by [[Total Recall Protocol]]."),
        ("Fly-To-Source Dive", "ui", "3D camera dive animation pinpointing reference nodes. Rendered in [[JARVIS Cyberpunk HUD]]."),
    ]

    for title, group, body in sample_topics:
        filename = title.lower().replace(" ", "_") + ".md"
        content = f"# {title}\n\n**Category**: `{group}`\n\n{body}\n\n## Details\n\nThis note is part of the JARVIS 3D Knowledge Galaxy."
        (notes_dir / filename).write_text(content, encoding="utf-8")


def scan_markdown_notes(base_dir: str = ".") -> dict:
    """
    Scan .md files in ./notes and ./captures, generating nodes & links for 3D force graph.
    """
    root = Path(base_dir).resolve()
    notes_dir = root / "notes"
    captures_dir = root / "captures"

    ensure_sample_notes(notes_dir)
    captures_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(notes_dir.glob("*.md")) + list(captures_dir.glob("*.md"))

    nodes = []
    title_to_index = {}

    for idx, filepath in enumerate(md_files):
        title = filepath.stem.replace("_", " ").title()
        group = filepath.parent.name
        content = filepath.read_text(encoding="utf-8", errors="replace")

        # Excerpt (~700 chars)
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
        excerpt = " ".join(lines)[:700] if lines else content[:700]

        nodes.append({
            "id": idx,
            "label": title,
            "group": group,
            "excerpt": excerpt,
            "path": str(filepath.relative_to(root)),
        })
        title_to_index[title.lower()] = idx
        title_to_index[filepath.stem.lower()] = idx

    links = []
    wikilink_re = re.compile(r'\[\[(.*?)\]\]')

    for idx, filepath in enumerate(md_files):
        content = filepath.read_text(encoding="utf-8", errors="replace")
        matches = wikilink_re.findall(content)

        # Connect via wikilinks
        for match in matches:
            target_clean = match.strip().lower()
            if target_clean in title_to_index and title_to_index[target_clean] != idx:
                links.append({
                    "source": idx,
                    "target": title_to_index[target_clean]
                })

        # Connect via title mentions (with word boundary checking)
        for other_title, other_idx in title_to_index.items():
            if other_idx != idx and len(other_title) > 4:
                pattern = r'\b' + re.escape(other_title) + r'\b'
                if re.search(pattern, content, re.IGNORECASE):
                    links.append({
                        "source": idx,
                        "target": other_idx
                    })

    # Deduplicate links
    unique_links = []
    seen = set()
    for link in links:
        pair = tuple(sorted([link["source"], link["target"]]))
        if pair not in seen:
            seen.add(pair)
            unique_links.append(link)

    return {"nodes": nodes, "links": unique_links}


def galaxy_chat(question: str, base_dir: str = ".") -> dict:
    """
    Score markdown notes against a question, return answer + array of note indices used.
    """
    graph_data = scan_markdown_notes(base_dir)
    nodes = graph_data["nodes"]

    if not nodes:
        return {"answer": "No notes indexed in the galaxy, sir.", "nodes": []}

    words = re.findall(r'\w+', question.lower())
    scored_nodes = []

    for node in nodes:
        score = 0
        text = (node["label"] + " " + node["excerpt"]).lower()
        for word in words:
            if len(word) > 2 and word in text:
                score += 1
                if word in node["label"].lower():
                    score += 3  # Extra weight for title matches

        if score > 0:
            scored_nodes.append((score, node))

    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    top_sources = [node for _, node in scored_nodes[:6]]

    if not top_sources:
        # Fallback to top 2 nodes if no keyword match
        top_sources = nodes[:2]

    source_indices = [n["id"] for n in top_sources]
    context = "\n\n".join([f"Note [{n['id']}] '{n['label']}': {n['excerpt']}" for n in top_sources])

    system_prompt = (
        "You are JARVIS, an impeccably polite British butler with razor wit. "
        "Address the user as 'sir' (occasionally, not every sentence). "
        "Answer the user's question using ONLY the provided notes context. "
        "Be extremely concise: ONE witty line plus the core factual answer. "
        "Do not recite the notes verbatim."
    )

    try:
        from core.bootstrap import build_assistant_runtime
        runtime = build_assistant_runtime()
        router = runtime.router
        messages = [{"role": "user", "content": f"Notes Context:\n{context}\n\nQuestion: {question}"}]
        answer = router.run(router.default, messages, system_prompt)
    except Exception:
        answer = f"Good evening, sir. Based on {len(top_sources)} notes: " + top_sources[0]["excerpt"][:200] + "..."

    return {"answer": answer, "nodes": source_indices}

