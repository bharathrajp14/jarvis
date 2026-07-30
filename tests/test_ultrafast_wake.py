# tests/test_ultrafast_wake.py — Unit tests for Ultrafast Wake Word Detection
from __future__ import annotations

import unittest
import numpy as np
from voice.whisper_local import transcribe_wake_fast, is_available


class TestUltrafastWakeDetection(unittest.TestCase):

    def test_transcribe_wake_fast_empty_buffer(self):
        res = transcribe_wake_fast(None)
        self.assertEqual(res, "")
        res_short = transcribe_wake_fast(b"short")
        self.assertEqual(res_short, "")

    def test_transcribe_wake_fast_silence(self):
        audio = np.zeros(16000, dtype=np.float32)
        res = transcribe_wake_fast(audio)
        self.assertIsInstance(res, str)

    def test_wake_phrase_matching(self):
        from voice.assistant import BRVoiceAssistant
        va = BRVoiceAssistant()
        self.assertTrue(va._is_wake_phrase("jarvis"))
        self.assertTrue(va._is_wake_phrase("javis"))
        self.assertTrue(va._is_wake_phrase("hey jarvis"))
        self.assertTrue(va._is_wake_phrase("hey javis"))
        self.assertTrue(va._is_wake_phrase("hi jarvis please"))

    def test_embedded_command_extraction(self):
        from voice.assistant import BRVoiceAssistant
        va = BRVoiceAssistant()
        cmd = va._extract_command_from_wake("hey jarvis open brave browser")
        self.assertEqual(cmd.strip(), "open brave browser")

        cmd_javis = va._extract_command_from_wake("javis check system status")
        self.assertEqual(cmd_javis.strip(), "check system status")


if __name__ == "__main__":
    unittest.main()
