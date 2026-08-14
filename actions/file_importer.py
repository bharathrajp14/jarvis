# actions/file_importer.py — BR-Jarvis Multi-File Knowledge Importer
"""
Multi-File Knowledge Importer Engine for BR JARVIS.
Ingests files (.txt, .pdf, .docx, .md, .csv, .xlsx, .vcf, .json) into:
1. Long-term memory store
2. ChromaDB / Vector Store for RAG similarity search
3. Contact Store (if .vcf or .csv contact list)
"""
from __future__ import annotations

import logging
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def import_file_to_knowledge(file_path: str | Path) -> Dict[str, Any]:
    """Ingest a file into JARVIS memory & vector store."""
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return {"status": "error", "message": f"File not found at '{file_path}'."}

    ext = p.suffix.lower()
    file_name = p.name
    text_content = ""

    try:
        if ext == ".vcf" or (ext == ".csv" and any(k in p.name.lower() for k in ["contact", "people", "phone", "address", "vcard", "export"])):
            # Trigger contact store import
            from memory.contact_manager import get_contact_store
            store = get_contact_store()
            if ext == ".vcf":
                res = store.import_vcf(p)
            else:
                res = store.import_csv(p)
            return {
                "status": "success",
                "type": "contacts",
                "file_name": file_name,
                "imported_count": res.get("imported_new", 0),
                "total_contacts": res.get("total_store", 0),
                "message": f"Successfully imported contacts from '{file_name}'. Total contacts in store: {res.get('total_store', 0)}.",
            }

        elif ext in (".txt", ".md", ".json", ".log", ".py", ".js", ".html", ".css", ".csv"):
            text_content = p.read_text(encoding="utf-8", errors="replace")

        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(p))
                pages = [page.extract_text() for page in reader.pages if page.extract_text()]
                text_content = "\n\n".join(pages)
            except Exception as pdf_err:
                text_content = f"[PDF file: {file_name}] (Text extraction error: {pdf_err})"

        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(str(p))
                text_content = "\n".join([para.text for para in doc.paragraphs if para.text])
            except Exception as docx_err:
                text_content = f"[DOCX file: {file_name}] (Text extraction error: {docx_err})"

        else:
            text_content = f"[File: {file_name}] (Binary file type '{ext}')"

    except Exception as e:
        return {"status": "error", "message": f"Failed to read file '{file_name}': {e}"}

    if not text_content.strip():
        return {"status": "warning", "message": f"File '{file_name}' contained no readable text."}

    # 1. Save to Persistent Memory
    try:
        from memory.persistent_store import MemoryEntry, save_memory
        entry = MemoryEntry(
            name=f"file_{p.stem}",
            description=f"Imported document: {file_name}",
            type="file_knowledge",
            content=text_content[:20000],  # Store first 20K chars
            scope="user",
        )
        save_memory(entry, scope="user")
    except Exception as e:
        logger.warning(f"[FileImporter] Warning: Persistent memory store failed: {e}")

    # 2. Save to Vector Store
    try:
        from memory.vector_store import TextSimilarityMemory
        mem_db = get_base_dir() / "memory_db" / "tf_idf_memory.json"
        vector_mem = TextSimilarityMemory(mem_db)
        vector_mem.store(
            text=f"Document: {file_name}\n\n{text_content[:8000]}",
            metadata={"file_name": file_name, "path": str(p), "type": ext},
        )
    except Exception as e:
        logger.warning(f"[FileImporter] Warning: Vector memory store failed: {e}")

    return {
        "status": "success",
        "type": "document",
        "file_name": file_name,
        "char_count": len(text_content),
        "message": f"Successfully imported '{file_name}' ({len(text_content)} characters) into persistent memory & vector search.",
    }
