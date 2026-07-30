# voice/sound_effects.py — JARVIS Acoustic Sound Effects & Low-Frequency Audio Chimes
"""
Generates futuristic acoustic audio cues:
1. High-frequency activation chime (1046 Hz -> 1318 Hz)
2. Deep resonant sub-bass listening pulse (180 Hz)
3. Low-frequency descending processing chime (240 Hz -> 160 Hz)
"""
from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("JARVIS.SoundEffects")

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False


import threading


def _run_async_sound(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()


def play_activation_beep() -> None:
    """Play bright ascending dual-tone activation chime (C6 -> E6)."""
    def _play():
        if _HAS_WINSOUND and sys.platform == "win32":
            try:
                winsound.Beep(1046, 60)  # C6
                winsound.Beep(1318, 80)  # E6
            except Exception as e:
                logger.debug(f"Activation chime failed: {e}")
    _run_async_sound(_play)


def play_deep_listening_bass() -> None:
    """Play deep resonant sub-bass acoustic listening pulse (180 Hz)."""
    def _play():
        if _HAS_WINSOUND and sys.platform == "win32":
            try:
                winsound.Beep(180, 100)  # Deep 180 Hz sub-bass
            except Exception as e:
                logger.debug(f"Deep bass sound failed: {e}")
    _run_async_sound(_play)


def play_processing_bass_chime() -> None:
    """Play smooth low-frequency descending processing chime (240 Hz -> 160 Hz)."""
    def _play():
        if _HAS_WINSOUND and sys.platform == "win32":
            try:
                winsound.Beep(240, 60)  # 240 Hz low tone
                winsound.Beep(160, 80)  # 160 Hz deep bass drop
            except Exception as e:
                logger.debug(f"Processing chime failed: {e}")
    _run_async_sound(_play)


def play_voice_detected_beep() -> None:
    """Play soft double micro-beep when user voice/speech is detected (880 Hz -> 987 Hz)."""
    def _play():
        if _HAS_WINSOUND and sys.platform == "win32":
            try:
                winsound.Beep(880, 30)   # A5
                winsound.Beep(987, 40)   # B5
            except Exception as e:
                logger.debug(f"Voice detected beep failed: {e}")
    _run_async_sound(_play)
