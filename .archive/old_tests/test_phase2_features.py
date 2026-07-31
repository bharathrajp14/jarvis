# tests/test_phase2_features.py — Verification unit tests for Web Extractor & Audio Equalizer
from __future__ import annotations

import unittest
from tools.web_extractor import extract_web_content, web_extractor_action
from voice.audio_eq import AudioEqualizer


class TestPhase2Features(unittest.TestCase):

    def test_web_extractor_action(self):
        res = web_extractor_action({"url": ""})
        self.assertIn("Error", res)

    def test_audio_equalizer(self):
        eq = AudioEqualizer(highpass_cutoff_hz=80, noise_gate_threshold=120)
        # Low noise chunk below threshold should be muted to 0s
        low_noise = b"\x05\x00" * 100
        processed = eq.process_pcm(low_noise)
        self.assertEqual(processed, b"\x00\x00" * 100)


if __name__ == "__main__":
    unittest.main()
