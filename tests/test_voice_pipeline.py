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

    def test_listening_chime(self):
        from voice.assistant import BRVoiceAssistant
        assistant = BRVoiceAssistant(ui=None)
        self.assertTrue(hasattr(assistant, "_play_listening_chime"))
        # Execute chime without error
        assistant._play_listening_chime()

    def test_sound_effects(self):
        from voice.sound_effects import play_activation_beep, play_deep_listening_bass, play_processing_bass_chime
        play_activation_beep()
        play_deep_listening_bass()
        play_processing_bass_chime()

    def test_recognizer_tuning(self):
        from voice.assistant import BRVoiceAssistant
        import speech_recognition as sr  # type: ignore
        assistant = BRVoiceAssistant(ui=None)
        r = sr.Recognizer()
        assistant._tune_recognizer(r)
        self.assertTrue(r.dynamic_energy_threshold)
        self.assertEqual(r.pause_threshold, 0.9)
        self.assertEqual(assistant._command_phrase_limit, 25.0)

    def test_stop_speech_barge_in(self):
        from voice.assistant import BRVoiceAssistant
        assistant = BRVoiceAssistant(ui=None)
        self.assertTrue(hasattr(assistant, "stop_speech"))
        assistant.stop_speech()

    def test_proxy_http_415_fallback(self):
        from backends.gemini import GeminiBackend
        backend = GeminiBackend()
        # Test transcribe with empty/dummy audio bytes handles exceptions gracefully
        res = backend.transcribe(b"RIFF....WAVE", mime_type="audio/wav")
        self.assertIsInstance(res, str)


if __name__ == "__main__":
    unittest.main()
