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
        self.assertEqual(r.pause_threshold, 0.45)
        self.assertEqual(assistant._command_phrase_limit, 20.0)

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

    def test_audio_ring_buffer(self):
        from voice.ring_buffer import AudioRingBuffer
        rb = AudioRingBuffer(buffer_duration_ms=500)
        # 16kHz 16-bit mono PCM = 32000 bytes/sec -> 500ms = 16000 bytes max
        chunk = b"\x00" * 8000
        rb.append(chunk)
        rb.append(chunk)
        self.assertEqual(len(rb.get_preroll_bytes()), 16000)
        rb.append(chunk)  # overflow drops oldest frame
        self.assertEqual(len(rb.get_preroll_bytes()), 16000)
        rb.clear()
        self.assertEqual(len(rb.get_preroll_bytes()), 0)

    def test_voice_assistant_backend_binding(self):
        from voice.assistant import BRVoiceAssistant
        assistant = BRVoiceAssistant(ui=None)
        self.assertIsNotNone(assistant.orchestrator)
        self.assertIsInstance(assistant.backends, dict)

    def test_javis_wake_word(self):
        from voice.assistant import BRVoiceAssistant
        assistant = BRVoiceAssistant(ui=None)
        self.assertTrue(assistant._is_wake_phrase("hey javis open chrome"))
        self.assertTrue(assistant._is_wake_phrase("javis check battery status"))
        cmd = assistant._extract_command_from_wake("hey javis open brave browser")
        self.assertEqual(cmd, "open brave browser")

    def test_repetition_collapsing_and_artifact_filtering(self):
        from voice.prompt_refiner import refine_voice_prompt, VoicePromptRefiner
        refiner = VoicePromptRefiner.get_instance()
        
        # Test collapse single-word repetition
        self.assertEqual(refiner.collapse_repetitions("hey, hey, hey, hey, hey"), "hey")
        self.assertEqual(refiner.collapse_repetitions("javis javis javis javis"), "javis")
        
        # Test collapse phrase repetition
        self.assertEqual(refiner.collapse_repetitions("hey javis, hey javis, hey javis"), "hey javis")
        
        # Test artifact rejection (pure wake words / fillers should yield refined = "")
        res1 = refine_voice_prompt("hey, javis, hey, javis, javis, javis, javis, javis")
        self.assertEqual(res1["refined"], "")
        
        res2 = refine_voice_prompt("hey, hey, hey, hey, hey, hey, hey")
        self.assertEqual(res2["refined"], "")
        
        # Test valid command with wake word & fillers & repetitions
        res3 = refine_voice_prompt("hey javis hey javis um please open chrome browser")
        self.assertEqual(res3["refined"], "Open chrome browser")

    def test_ui_send_no_duplicate_log(self):
        from ui.main_window import MainWindow
        logs = []
        win = MainWindow.__new__(MainWindow)
        class DummyInput:
            def text(self): return "open youtube latest anime in tamil voice over"
            def clear(self): pass
        class DummyLog:
            def append_log(self, msg): logs.append(msg)
        win._input = DummyInput()
        win._log = DummyLog()
        win.on_text_command = lambda cmd: logs.append(f"ON_TEXT:{cmd}")
        win._send()
        # Ensure 'You: ...' is NOT logged directly in _send when on_text_command handler is bound
        self.assertNotIn("You: open youtube latest anime in tamil voice over", logs)



if __name__ == "__main__":
    unittest.main()
