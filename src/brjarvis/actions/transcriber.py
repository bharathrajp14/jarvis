# actions/transcriber.py — JARVIS MK37 Offline Transcription
"""
Offline audio and video file transcription using local Whisper.
Supports: MP3, WAV, M4A, OGG, FLAC, MP4, MKV, AVI, WEBM.
Output formats: TXT, SRT, VTT, JSON.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def transcribe_file(
    file_path: str,
    language: str = "auto",
    output_format: str = "txt",
) -> dict:
    """
    Transcribe an audio or video file to text offline.

    Args:
        file_path: Path to the audio/video file.
        language: Language code ('en', 'hi', 'fr', etc.) or 'auto' for detection.
        output_format: Output format: 'txt', 'srt', 'vtt', 'json'.

    Returns:
        dict with 'text', 'output_path', 'language', 'segments', 'error'.
    """
    try:
        from voice.whisper_local import transcribe_file as whisper_transcribe
        return whisper_transcribe(file_path, language, output_format)
    except ImportError:
        return {"error": "Local Whisper is not installed. Install faster-whisper or openai-whisper."}
    except Exception as e:
        return {"error": f"Transcription failed: {e}"}


def transcribe_batch(
    file_paths: list[str],
    language: str = "auto",
    output_format: str = "txt",
) -> list[dict]:
    """
    Transcribe multiple files in batch.

    Args:
        file_paths: List of paths to audio/video files.
        language: Language code or 'auto'.
        output_format: Output format.

    Returns:
        List of result dicts for each file.
    """
    results = []
    for fp in file_paths:
        result = transcribe_file(fp, language, output_format)
        result["input_file"] = fp
        results.append(result)
    return results


def supported_formats() -> dict:
    """Return supported audio/video formats."""
    return {
        "audio": [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma", ".aac"],
        "video": [".mp4", ".mkv", ".avi", ".webm", ".mov", ".flv", ".wmv"],
        "output": ["txt", "srt", "vtt", "json"],
    }
