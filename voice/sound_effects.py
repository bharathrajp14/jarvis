# voice/sound_effects.py — JARVIS Acoustic Sound Effects & Low-Frequency Audio Chimes
"""
Generates futuristic acoustic audio cues with smooth PCM sine wave synthesis:
1. High-frequency activation chime (1046 Hz -> 1318 Hz)
2. Deep resonant sub-bass listening pulse (180 Hz)
3. Low-frequency descending processing chime (240 Hz -> 160 Hz)
4. Soft voice detected double micro-chime (880 Hz -> 987 Hz)

Supports environment control: JARVIS_ENABLE_SOUND_EFFECTS (default: true).
Uses winsound.PlaySound memory WAV playback on Windows (zero audio device conflicts).
"""
from __future__ import annotations

import io
import logging
import math
import os
import struct
import sys
import threading
import wave

logger = logging.getLogger("JARVIS.SoundEffects")

_HAS_WINSOUND = False
try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False

_HAS_SOUNDDEVICE = False
try:
    import numpy as np
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except ImportError:
    _HAS_SOUNDDEVICE = False


def is_sound_enabled() -> bool:
    """Check environment variable if sound effects are enabled."""
    val = os.environ.get("JARVIS_ENABLE_SOUND_EFFECTS", "true").lower().strip()
    return val in ("true", "1", "yes", "on", "active")


def _run_async_sound(fn):
    if not is_sound_enabled():
        return
    t = threading.Thread(target=fn, daemon=True)
    t.start()


def _create_sine_wav_bytes(freqs: list[int], durations: list[int], volume: float = 0.12, sample_rate: int = 44100) -> bytes:
    """Generate 16-bit mono PCM WAV bytes in memory with smooth attack/decay envelope."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        
        frames = []
        for freq, dur in zip(freqs, durations):
            num_samples = int(sample_rate * (dur / 1000.0))
            fade_in = int(sample_rate * 0.004)
            fade_out = int(sample_rate * 0.008)
            
            for i in range(num_samples):
                t = i / float(sample_rate)
                val = math.sin(2.0 * math.pi * freq * t) * volume
                if i < fade_in:
                    val *= (i / float(fade_in))
                elif i > num_samples - fade_out:
                    val *= ((num_samples - i) / float(fade_out))
                sample = int(val * 32767.0)
                sample = max(-32768, min(32767, sample))
                frames.append(struct.pack('<h', sample))
                
        wf.writeframes(b''.join(frames))
    return buf.getvalue()


def _play_pcm_chime(freqs: list[int], durations: list[int], volume: float = 0.12) -> bool:
    """Play soft sine wave tones without audio device conflicts."""
    # 1. Primary Engine for Windows: winsound.PlaySound with in-memory WAV
    if _HAS_WINSOUND and sys.platform == "win32":
        try:
            wav_bytes = _create_sine_wav_bytes(freqs, durations, volume=volume)
            winsound.PlaySound(wav_bytes, winsound.SND_MEMORY | winsound.SND_ASYNC)
            return True
        except Exception as e:
            logger.debug(f"winsound.PlaySound memory chime failed: {e}")

    # 2. Secondary Engine for Non-Windows / Fallback: sounddevice
    if _HAS_SOUNDDEVICE:
        try:
            sample_rate = 44100
            chunks = []
            for freq, dur in zip(freqs, durations):
                t = np.linspace(0, dur / 1000.0, int(sample_rate * (dur / 1000.0)), False)
                wave_arr = np.sin(2 * np.pi * freq * t) * volume
                fade_in = int(sample_rate * 0.004)
                fade_out = int(sample_rate * 0.008)
                if len(wave_arr) > fade_in + fade_out:
                    wave_arr[:fade_in] *= np.linspace(0, 1, fade_in)
                    wave_arr[-fade_out:] *= np.linspace(1, 0, fade_out)
                chunks.append(wave_arr.astype(np.float32))
            full_audio = np.concatenate(chunks).astype(np.float32).reshape(-1, 1)
            sd.play(full_audio, sample_rate)
            sd.wait()
            return True
        except Exception as e:
            logger.debug(f"sounddevice PCM playback error: {e}")

    # 3. Last Resort Fallback: winsound.Beep
    if _HAS_WINSOUND and sys.platform == "win32":
        try:
            for freq, dur in zip(freqs, durations):
                winsound.Beep(freq, dur)
            return True
        except Exception as e:
            logger.debug(f"winsound.Beep fallback error: {e}")

    return False


def play_activation_beep() -> None:
    """Play soft ascending dual-tone wake activation chime (C6 -> E6)."""
    def _play():
        _play_pcm_chime([1046, 1318], [55, 75], volume=0.15)
    _run_async_sound(_play)


def play_deep_listening_bass() -> None:
    """Play deep resonant sub-bass acoustic listening pulse (180 Hz)."""
    def _play():
        _play_pcm_chime([180], [90], volume=0.15)
    _run_async_sound(_play)


def play_processing_bass_chime() -> None:
    """Play smooth low-frequency descending processing chime (240 Hz -> 160 Hz)."""
    def _play():
        _play_pcm_chime([240, 160], [50, 70], volume=0.12)
    _run_async_sound(_play)


def play_voice_detected_beep() -> None:
    """Play soft double micro-beep when user voice/speech is detected (880 Hz -> 987 Hz)."""
    def _play():
        _play_pcm_chime([880, 987], [25, 35], volume=0.10)
    _run_async_sound(_play)
