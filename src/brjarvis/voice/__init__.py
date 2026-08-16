# voice/__init__.py — JARVIS MK37 Voice Control Package
"""
Voice package re-exporting TTS, STT, and Assistant engines.
"""
from __future__ import annotations

from .tts import NeuralTTS, MCIPlayer
from .stt import SounddeviceMicrophone
from .assistant import BRVoiceAssistant

__all__ = [
    "NeuralTTS",
    "MCIPlayer",
    "SounddeviceMicrophone",
    "BRVoiceAssistant",
]
