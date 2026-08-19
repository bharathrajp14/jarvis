# tools/transcription_tools.py — JARVIS MK37 Transcription Tools Plugin
"""
Registers offline audio/video transcription tools in the JARVIS tool registry.
"""

from __future__ import annotations

import json

from .registry import register_tool


@register_tool(
    name="transcribe_file",
    description="Transcribe an audio or video file to text offline using local Whisper. Supports MP3, WAV, M4A, MP4, MKV, AVI, WEBM. Outputs TXT, SRT subtitles, VTT, or JSON.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the audio or video file"},
            "language": {
                "type": "string",
                "description": "Language code (e.g., 'en', 'hi') or 'auto' for detection (default: auto)",
            },
            "output_format": {
                "type": "string",
                "description": "Output format: 'txt', 'srt', 'vtt', 'json' (default: txt)",
            },
        },
        "required": ["file_path"],
    },
)
def tool_transcribe_file(args: dict) -> str:
    from brjarvis.actions.transcriber import transcribe_file

    result = transcribe_file(
        args["file_path"],
        args.get("language", "auto"),
        args.get("output_format", "txt"),
    )
    return json.dumps(result, indent=2, default=str)


@register_tool(
    name="transcribe_batch",
    description="Transcribe multiple audio/video files in batch. Returns results for each file.",
    parameters={
        "type": "object",
        "properties": {
            "file_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of paths to audio/video files",
            },
            "language": {"type": "string", "description": "Language code or 'auto' (default: auto)"},
            "output_format": {"type": "string", "description": "Output format (default: txt)"},
        },
        "required": ["file_paths"],
    },
)
def tool_transcribe_batch(args: dict) -> str:
    from brjarvis.actions.transcriber import transcribe_batch

    results = transcribe_batch(
        args["file_paths"],
        args.get("language", "auto"),
        args.get("output_format", "txt"),
    )
    return json.dumps(results, indent=2, default=str)
