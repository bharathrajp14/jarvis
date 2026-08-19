# skills/builtin_rag.py — BR-JARVIS MK37 RAG & Semantic Retrieval Skills
"""
RAG (Retrieval-Augmented Generation) and Semantic Search skills for BR-JARVIS MK37.
Importing this module registers skills for document Q&A, knowledge base querying, and semantic indexing.
"""

from __future__ import annotations

from .loader import SkillDef, register_builtin_skill

_CHAT_PDF_PROMPT = """\
You are a document analysis expert. Chat with and extract insights from documents using the RAG engine.

## Task
$ARGUMENTS

## Execution Protocol
1. If a file path is provided, ingest it into knowledge memory using `rag_ingest(file_path=...)` or `import_file_to_knowledge`.
2. Use `rag_query(query=...)` or `rag_chat` to search the indexed library chunks for relevant context.
3. Synthesize the retrieved excerpts into a comprehensive, citation-backed answer.
4. Always cite specific section headings or page numbers where the information originated.
"""

_CHAT_WEBPAGE_PROMPT = """\
You are a web document analyst. Extract and answer deep questions about web pages and online articles.

## Task
$ARGUMENTS

## Execution Protocol
1. Ingest the web content into knowledge memory using `rag_ingest_webpage(url=...)`.
2. Use `rag_query(query=...)` to retrieve the relevant semantic sections.
3. Provide a clear, structured summary and answer referencing key statements from the web source.
"""

_LIBRARY_PROMPT = """\
You are the BR-JARVIS Knowledge Library Manager. Help the user organize, inspect, and query documents in knowledge storage.

## Task
$ARGUMENTS

## Execution Protocol
1. Call `rag_list` to view all currently indexed documents in the knowledge base.
2. Ingest new documents with `rag_ingest` or web URLs with `rag_ingest_webpage`.
3. Query the knowledge base across all documents with `rag_query`.
4. Delete obsolete files from the index using `rag_delete`.
5. Summarize knowledge base status and total indexed entries.
"""

_SEMANTIC_SEARCH_PROMPT = """\
Perform vector-based semantic code and document search across the workspace.

## Query
$ARGUMENTS

## Execution Protocol
1. Call `file_search_semantic` or `semantic_file_search` with the search query.
2. Rank the top semantic matches across files, classes, and markdown documentation.
3. Summarize matching code blocks with file paths and line numbers.
"""


def _register_rag_builtins() -> None:
    register_builtin_skill(
        SkillDef(
            name="chat-pdf",
            description="Chat with and analyze PDF or document files using RAG knowledge indexing",
            triggers=["/chat-pdf", "/pdf", "chat with pdf", "read this pdf", "analyze this document"],
            tools=["rag_ingest", "rag_query", "rag_chat", "import_file_to_knowledge", "file_read"],
            prompt=_CHAT_PDF_PROMPT,
            file_path="builtin:chat-pdf",
            category="research",
            domain="Knowledge & RAG",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="chat-webpage",
            description="Ingest and query web pages via semantic RAG retrieval",
            triggers=["/chat-webpage", "/webpage", "chat with webpage", "analyze this website"],
            tools=["rag_ingest_webpage", "rag_query", "rag_chat", "fetch_page"],
            prompt=_CHAT_WEBPAGE_PROMPT,
            file_path="builtin:chat-webpage",
            category="research",
            domain="Knowledge & RAG",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="library",
            description="Manage personal document knowledge base (list, ingest, search, delete)",
            triggers=["/library", "/rag", "document library", "my documents", "knowledge base"],
            tools=["rag_list", "rag_ingest", "rag_ingest_webpage", "rag_query", "rag_delete"],
            prompt=_LIBRARY_PROMPT,
            file_path="builtin:library",
            category="research",
            domain="Knowledge & RAG",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="semantic_search",
            description="Search workspace files and documentation using semantic vector similarity",
            triggers=["/semantic-search", "/vector-search", "semantic search"],
            tools=["file_search_semantic", "semantic_file_search", "rag_query"],
            prompt=_SEMANTIC_SEARCH_PROMPT,
            file_path="builtin:semantic_search",
            category="engineering",
            domain="Semantic Retrieval",
            user_invocable=True,
            source="builtin",
        )
    )


_register_rag_builtins()
