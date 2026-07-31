# tools/file_processor_tools.py — Universal File Processor Tool Wrappers
from __future__ import annotations

from pathlib import Path
from tools.registry import register_tool
from actions.file_processor import file_processor, _detect_type


@register_tool(
    name="process_universal_file",
    description="Process, analyze, read, convert, OCR, or summarize any file type (image, PDF, DOCX, CSV, XLSX, JSON, Audio, Video, ZIP).",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or relative path to target file."},
            "action": {"type": "string", "description": "Action to perform: 'summarize', 'ocr', 'describe', 'convert', 'analyze', 'extract_text', 'resize', 'info'."},
            "instruction": {"type": "string", "description": "Specific instruction or query for analysis."}
        },
        "required": ["file_path"]
    }
)
def tool_process_universal_file(file_path: str, action: str = "summarize", instruction: str = "") -> str:
    path = Path(file_path).resolve()
    if not path.exists():
        return f"File not found: {file_path}"
    params = {"file_path": str(path), "action": action, "instruction": instruction}
    return file_processor(params)
