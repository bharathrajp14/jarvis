# tests/test_phase3_features.py — Verification unit tests for System Health & Emotion Analyzer
from __future__ import annotations

import unittest
from tools.system_health import get_system_health, system_health_action
from voice.emotion_analyzer import EmotionAnalyzer


class TestPhase3Features(unittest.TestCase):

    def test_system_health_action(self):
        info = get_system_health()
        self.assertIsInstance(info, dict)
        res = system_health_action({})
        self.assertIn("System Health", res)

    def test_emotion_analyzer(self):
        analyzer = EmotionAnalyzer()
        pcm_bytes = b"\x10\x00\x20\x00" * 200
        res = analyzer.analyze_audio_emotion(pcm_bytes)
        self.assertIn("emotion", res)
        self.assertIn(res["emotion"], ("Calm", "Focused", "Urgent", "Neutral"))


if __name__ == "__main__":
    unittest.main()
