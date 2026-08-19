# tools/file_import_tools.py — BR-Jarvis Universal File Ingestion Tools Plugin
"""
Universal File Ingestion Tools Plugin for JARVIS.
Exposes tools to import files (.txt, .pdf, .docx, .md, .csv, .xlsx, .vcf)
into persistent knowledge memory & vector similarity search.
"""

from __future__ import annotations

from brjarvis.actions.file_importer import import_file_to_knowledge

from .registry import register_tool


@register_tool(
    name="import_file_to_knowledge",
    description="Import a document (.txt, .pdf, .docx, .md, .csv, .vcf) from local filesystem into JARVIS's persistent memory & vector search.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or workspace-relative path to document file"}
        },
        "required": ["file_path"],
    },
)
def tool_import_file_to_knowledge(args: dict) -> str:
    """Import document or file into memory."""
    path_str = (
        args
        if isinstance(args, str)
        else str(args.get("file_path") or args.get("path") or args.get("file") or "").strip()
    )
    if not path_str:
        return "Error: Provide a 'file_path' to import."

    res = import_file_to_knowledge(path_str)
    if res["status"] == "success":
        return f"📄 {res['message']}"
    return f"❌ Import failed: {res['message']}"
