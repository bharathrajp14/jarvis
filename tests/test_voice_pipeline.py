# tests/test_voice_pipeline.py — Unit tests for Voice Prompt Refinement Engine
from __future__ import annotations

import unittest
from voice.prompt_refiner import VoicePromptRefiner, refine_voice_prompt


class TestVoicePipeline(unittest.TestCase):

    def setUp(self):
        self.refiner = VoicePromptRefiner()

    def test_strip_fillers(self):
        raw = "um uh jarvis check system memory and open chrome"
        cleaned = self.refiner.strip_fillers(raw)
        self.assertNotIn("um", cleaned)
        self.assertNotIn("uh", cleaned)
        self.assertNotIn("jarvis", cleaned)
        self.assertIn("check system memory", cleaned)

    def test_refine_voice_prompt(self):
        raw = "um jarvis please can you open chrome browser"
        res = refine_voice_prompt(raw)
        self.assertTrue(res["was_modified"])
        self.assertEqual(res["raw"], raw)
        self.assertIn("Open chrome browser", res["refined"])

    def test_empty_speech(self):
        res = refine_voice_prompt("   ")
        self.assertFalse(res["was_modified"])
        self.assertEqual(res["refined"], "")


if __name__ == "__main__":
    unittest.main()
