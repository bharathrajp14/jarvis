# skills/builtin_rag.py — JARVIS MK37 RAG Skills
"""
RAG (Retrieval-Augmented Generation) skills for JARVIS MK37.
Importing this module registers skills for document chat, library management.
"""
from __future__ import annotations
from .loader import SkillDef, register_builtin_skill


_CHAT_PDF_PROMPT = """\
You are a document analysis expert. Chat with and answer questions about
a document that the user has loaded into the library.

## Task
$ARGUMENTS

## Steps
1. If a file path is given, first ingest it with rag_ingest.
2. Use rag_query to search the library for relevant content.
3. Synthesize the retrieved chunks into a clear, comprehensive answer.
4. Cite the source document and chunk when referencing specific information.

## Rules
- Only answer based on information found in the documents.
- If the document doesn't contain the answer, say so clearly.
- Quote relevant passages when appropriate.
- For multi-document queries, compare and contrast information.
"""

_CHAT_WEBPAGE_PROMPT = """\
You are a web content analyst. Analyze and answer questions about a webpage.

## Task
$ARGUMENTS

## Steps
1. If a URL is provided, ingest it with rag_ingest_webpage.
2. Use rag_query to search for relevant content.
3. Provide a clear answer based on the webpage content.

## Rules
- Only use information from the actual webpage content.
- Note if the information might be outdated.
"""

_LIBRARY_PROMPT = """\
You are a document library manager. Help the user manage their document library.

## Task
$ARGUMENTS

## Steps
1. Use rag_list to show current documents.
2. If the user wants to add: use rag_ingest or rag_ingest_webpage.
3. If the user wants to search: use rag_query.
4. If the user wants to delete: use rag_delete.
5. If the user wants to chat: use rag_chat.

## Available Commands
- List all documents
- Add a file or webpage
- Search for information
- Delete a document
- Ask questions about documents
"""


register_builtin_skill(SkillDef(
    name="chat-pdf",
    triggers=["/chat-pdf", "/pdf", "chat with pdf", "read this pdf", "analyze this document"],
    description="Chat with a PDF or document using RAG.",
    prompt=_CHAT_PDF_PROMPT,
    tools=[],
    file_path="",
    user_invocable=True,
))

register_builtin_skill(SkillDef(
    name="chat-webpage",
    triggers=["/chat-webpage", "/webpage", "chat with webpage", "analyze this website"],
    description="Chat with a webpage by ingesting and querying its content.",
    prompt=_CHAT_WEBPAGE_PROMPT,
    tools=[],
    file_path="",
    user_invocable=True,
))

register_builtin_skill(SkillDef(
    name="library",
    triggers=["/library", "/rag", "document library", "my documents"],
    description="Manage your personal document library (add, search, delete).",
    prompt=_LIBRARY_PROMPT,
    tools=[],
    file_path="",
    user_invocable=True,
))
