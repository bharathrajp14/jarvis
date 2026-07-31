# voice/gemini_stt.py — Dedicated Gemini Flash Audio Listening & STT Engine
"""
Dedicated Online Speech-to-Text (STT) Engine for BR JARVIS.
Uses GEMINI_LISTEN_API_KEY strictly for audio transcription via Gemini Flash REST API.
Operates 100% in-memory with automatic fallback to local CTranslate2 faster-whisper.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("JARVIS.GeminiSTT")

DEFAULT_LISTEN_MODEL = "gemini-flash-latest"


def get_listen_api_key() -> str:
    """Get the dedicated Gemini listening API key from env or config/api_keys.json."""
    key = os.environ.get("GEMINI_LISTEN_API_KEY", "").strip()
    if key and not key.startswith("your_"):
        return key

    try:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "api_keys.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
            listen_key = data.get("gemini_listen_api_key", "").strip()
            if listen_key:
                return listen_key
    except Exception as e:
        logger.debug(f"Failed to read api_keys.json for listen key: {e}")

    return ""


def transcribe_audio_online(audio_bytes: bytes, timeout_seconds: float = 4.5) -> str:
    """
    Transcribe audio WAV bytes using dedicated Gemini Listen API key.
    Sends base64 audio/wav data to gemini-flash-latest REST API.
    Returns clean transcript string or empty string on error/timeout.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return ""

    key = get_listen_api_key()
    if not key:
        logger.debug("No GEMINI_LISTEN_API_KEY configured for online STT.")
        return ""

    try:
        import httpx
    except ImportError:
        logger.debug("httpx not installed for Gemini STT.")
        return ""

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

    models_to_try = [
        "gemini-flash-latest",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
    ]

    prompt_text = (
        "Transcribe the spoken audio verbatim in English without adding commentary, "
        "introductory phrases, or formatting."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
                            "data": b64_audio,
                        }
                    },
                    {"text": prompt_text},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 250,
        },
    }

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": key,
        }

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "").strip()
                            if raw_text:
                                logger.info(f"Gemini STT ({model_name}) transcribed: '{raw_text}'")
                                return raw_text
                else:
                    logger.debug(f"Gemini STT {model_name} returned status {res.status_code}: {res.text[:150]}")
        except Exception as e:
            logger.debug(f"Gemini STT {model_name} attempt error: {e}")

    return ""
