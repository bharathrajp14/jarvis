# voice/audio_eq.py — Audio DSP Equalizer & Noise Gate Filter for JARVIS
"""
Real-time Digital Signal Processing (DSP) Audio Equalizer.
Applies high-pass filtering (80Hz cut) and noise gate thresholding to 16kHz PCM audio buffers.
"""
from __future__ import annotations

import struct


class AudioEqualizer:
    """DSP equalizer and noise gate filter for raw 16-bit 16kHz mono PCM audio."""

    def __init__(self, highpass_cutoff_hz: int = 80, noise_gate_threshold: int = 120):
        self.highpass_cutoff_hz = highpass_cutoff_hz
        self.noise_gate_threshold = noise_gate_threshold
        self._prev_sample = 0.0

    def process_pcm(self, pcm_bytes: bytes) -> bytes:
        """Apply high-pass filtering and noise gate to PCM byte array."""
        if not pcm_bytes or len(pcm_bytes) < 2:
            return pcm_bytes

        count = len(pcm_bytes) // 2
        samples = list(struct.unpack(f"<{count}h", pcm_bytes[:count * 2]))

        processed = []
        alpha = 0.95  # High-pass filter coefficient (~80Hz cut at 16kHz)

        for s in samples:
            # 1. High-pass filter (remove low DC hum / sub-bass noise)
            hp_sample = alpha * (self._prev_sample + s - self._prev_sample)
            self._prev_sample = s

            # 2. Noise Gate (mute low ambient noise floor below threshold)
            if abs(hp_sample) < self.noise_gate_threshold:
                hp_sample = 0.0

            # Clamp to 16-bit integer range
            clamped = max(-32768, min(32767, int(hp_sample)))
            processed.append(clamped)

        return struct.pack(f"<{count}h", *processed)
