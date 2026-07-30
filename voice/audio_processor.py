# voice/audio_processor.py — Audio Signal Processing & Noise Floor Filter for JARVIS MK37
"""
Provides Voice Activity Detection (VAD), RMS audio noise floor estimation,
auto-gain adjustment, and silence filtering for robust speech input.
"""
from __future__ import annotations

import math
import struct
from typing import Tuple


class AudioProcessor:
    """Real-time PCM audio buffer analysis and noise suppression filter."""

    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0) * 2)  # 16-bit mono = 2 bytes per sample
        self.noise_floor = 300.0

    def calculate_rms(self, pcm_data: bytes) -> float:
        """Calculate Root Mean Square (RMS) energy level of 16-bit PCM audio samples using NumPy."""
        if not pcm_data or len(pcm_data) < 2:
            return 0.0
        
        try:
            import numpy as np
            num_samples = len(pcm_data) // 2
            shorts = np.frombuffer(pcm_data[:num_samples * 2], dtype=np.int16)
            if len(shorts) == 0:
                return 0.0
            return float(np.sqrt(np.mean(shorts.astype(np.float32) ** 2)))
        except Exception:
            return 0.0

    def update_noise_floor(self, pcm_data: bytes, alpha: float = 0.05) -> float:
        """Dynamically update ambient noise floor estimation during quiet periods."""
        rms = self.calculate_rms(pcm_data)
        if rms > 0:
            self.noise_floor = (1 - alpha) * self.noise_floor + alpha * rms
        return self.noise_floor

    def is_speech_present(self, pcm_data: bytes, threshold_multiplier: float = 2.2) -> bool:
        """Check if audio frame exceeds dynamic noise floor speech threshold (VAD)."""
        rms = self.calculate_rms(pcm_data)
        threshold = max(self.noise_floor * threshold_multiplier, 350.0)
        return rms >= threshold

    def normalize_pcm(self, pcm_data: bytes, target_peak: int = 24000) -> bytes:
        """Apply dynamic auto-gain control to PCM audio bytes using NumPy vectorization."""
        if not pcm_data or len(pcm_data) < 2:
            return pcm_data
        
        try:
            import numpy as np
            num_samples = len(pcm_data) // 2
            shorts = np.frombuffer(pcm_data[:num_samples * 2], dtype=np.int16)
            if len(shorts) == 0:
                return pcm_data
            
            max_val = int(np.max(np.abs(shorts))) or 1
            if max_val >= target_peak:
                return pcm_data
            
            scale = min(target_peak / max_val, 4.0)
            scaled = np.clip(shorts.astype(np.float32) * scale, -32768, 32767).astype(np.int16)
            return scaled.tobytes()
        except Exception:
            return pcm_data
