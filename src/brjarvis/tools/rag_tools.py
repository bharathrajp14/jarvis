# tools/rag_tools.py — JARVIS MK37 RAG Tools Plugin
"""
Registers LocalLibrary RAG tools in the JARVIS tool registry.
Enables document ingestion, querying, and RAG-augmented chat.
"""
from __future__ import annotations

import json
from .registry import register_tool


@register_tool(
    name="rag_ingest",
    description="Ingest a document (PDF, DOCX, TXT, CSV, MD) into the local RAG library for later querying. Provide the file path.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the document file to ingest"},
            "doc_name": {"type": "string", "description": "Optional custom name for the document"},
        },
        "required": ["file_path"],
    }
)
def tool_rag_ingest(args: dict) -> str:
    from brjarvis.actions.rag_library import ingest_file
    result = ingest_file(args["file_path"], args.get("doc_name"))
    return json.dumps(result, indent=2)


@register_tool(
    name="rag_ingest_webpage",
    description="Ingest a webpage into the local RAG library by fetching and indexing its content.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL of the webpage to ingest"},
            "doc_name": {"type": "string", "description": "Optional custom name for the document"},
        },
        "required": ["url"],
    }
)
def tool_rag_ingest_webpage(args: dict) -> str:
    from brjarvis.actions.rag_library import ingest_webpage
    result = ingest_webpage(args["url"], args.get("doc_name"))
    return json.dumps(result, indent=2)


@register_tool(
    name="rag_query",
    description="Search the local document library for information relevant to a question. Returns the most relevant text chunks.",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The search query or question"},
            "top_k": {"type": "integer", "description": "Number of results (default: 5)"},
            "doc_filter": {"type": "string", "description": "Optional: filter to a specific document name"},
        },
        "required": ["question"],
    }
)
def tool_rag_query(args: dict) -> str:
    from brjarvis.actions.rag_library import query
    results = query(args["question"], args.get("top_k", 5), args.get("doc_filter"))
    if not results:
        return "No relevant documents found."
    return json.dumps(results, indent=2, default=str)


@register_tool(
    name="rag_chat",
    description="Chat with your personal document library. Ask questions and get AI-generated answers based on your ingested documents.",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Your question about the documents"},
            "doc_filter": {"type": "string", "description": "Optional: filter to a specific document"},
        },
        "required": ["question"],
    }
)
def tool_rag_chat(args: dict) -> str:
    from brjarvis.actions.rag_library import rag_chat
    return rag_chat(args["question"], doc_filter=args.get("doc_filter"))


@register_tool(
    name="rag_list",
    description="List all documents currently in the local RAG library.",
    parameters={}
)
def tool_rag_list(args: dict) -> str:
    from brjarvis.actions.rag_library import list_documents
    docs = list_documents()
    if not docs:
        return "No documents in the library. Use rag_ingest to add documents."
    return json.dumps(docs, indent=2, default=str)


@register_tool(
    name="rag_delete",
    description="Delete a document from the local RAG library by name.",
    parameters={
        "type": "object",
        "properties": {
            "doc_name": {"type": "string", "description": "Name of the document to delete"},
        },
        "required": ["doc_name"],
    }
)
def tool_rag_delete(args: dict) -> str:
    from brjarvis.actions.rag_library import delete_document
    result = delete_document(args["doc_name"])
    return json.dumps(result, indent=2)
