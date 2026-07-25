# tests/test_nextgen_features.py — Verification unit tests for Window Manager & Speaker Biometrics
from __future__ import annotations

import unittest
from tools.window_manager import list_desktop_windows, window_manager_action
from voice.speaker_id import SpeakerVerifier


class TestNextGenFeatures(unittest.TestCase):

    def test_window_manager_list(self):
        res = list_desktop_windows()
        self.assertIsInstance(res, list)

    def test_window_manager_action(self):
        res = window_manager_action({"action": "list"})
        self.assertIsInstance(res, str)
        self.assertIn("Desktop Windows", res)

    def test_speaker_verifier(self):
        verifier = SpeakerVerifier()
        # 16kHz 16-bit PCM silent chunk
        silent_pcm = b"\x00" * 3200
        res_silent = verifier.verify_speaker(silent_pcm)
        self.assertFalse(res_silent["is_verified"])

        # Simulated audio wave
        audio_wave = bytes([int(100 * math.sin(i * 0.1)) & 0xFF for i in range(3200)])
        res_wave = verifier.verify_speaker(audio_wave)
        self.assertIsInstance(res_wave, dict)


import math

if __name__ == "__main__":
    unittest.main()
