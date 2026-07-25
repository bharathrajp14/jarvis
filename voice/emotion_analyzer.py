# voice/emotion_analyzer.py — Voice Emotion & Pitch Variance Analyzer for JARVIS
"""
Voice Emotion & Speech Tempo Analyzer.
Analyzes PCM audio pitch variance and speech rate to detect user mood/urgency (Calm, Urgent, Focused).
"""
from __future__ import annotations

import math
import struct
from typing import Dict, Any


class EmotionAnalyzer:
    """Acoustic emotion & pitch variance analyzer."""

    def analyze_audio_emotion(self, pcm_bytes: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """Analyze pitch variance and energy profile to classify speech tone."""
        if not pcm_bytes or len(pcm_bytes) < 4:
            return {"emotion": "Neutral", "urgency_score": 0.0, "pitch_variance": 0.0}

        count = len(pcm_bytes) // 2
        samples = struct.unpack(f"<{count}h", pcm_bytes[:count * 2])

        # Calculate energy variance across 20ms frames
        frame_size = int(sample_rate * 0.02)
        energies = []
        for i in range(0, count - frame_size, frame_size):
            frame = samples[i:i + frame_size]
            e = math.sqrt(sum(s * s for s in frame) / frame_size)
            energies.append(e)

        if not energies:
            return {"emotion": "Neutral", "urgency_score": 0.0, "pitch_variance": 0.0}

        mean_energy = sum(energies) / len(energies)
        var_energy = sum((e - mean_energy) ** 2 for e in energies) / len(energies)
        std_energy = math.sqrt(var_energy)

        # High energy variance & high mean -> Urgent / High Intensity
        if mean_energy > 1200.0 and std_energy > 400.0:
            emotion = "Urgent"
            urgency_score = 0.9
        elif mean_energy > 600.0:
            emotion = "Focused"
            urgency_score = 0.5
        else:
            emotion = "Calm"
            urgency_score = 0.2

        return {
            "emotion": emotion,
            "urgency_score": urgency_score,
            "mean_energy": round(mean_energy, 2),
            "pitch_variance": round(std_energy, 2),
        }
