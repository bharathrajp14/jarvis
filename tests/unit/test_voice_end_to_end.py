# tests/unit/test_voice_end_to_end.py — End-to-End Voice Interaction Tests
from __future__ import annotations

import asyncio
import unittest
from voice.assistant import BRVoiceAssistant
from voice.prompt_refiner import refine_voice_prompt
from voice.state_machine import VoiceState


class TestVoiceEndToEnd(unittest.TestCase):

    def setUp(self):
        self.assistant = BRVoiceAssistant(ui=None)

    def test_strict_wake_word_policy(self):
        # Valid wake phrases
        self.assertTrue(self.assistant._is_wake_phrase("jarvis"))
        self.assistant._last_wake_time = 0.0
        self.assertTrue(self.assistant._is_wake_phrase("hey jarvis"))
        self.assistant._last_wake_time = 0.0
        self.assertTrue(self.assistant._is_wake_phrase("ok jarvis what time is it"))

        # Rejection of broad/noisy false positives
        self.assistant._last_wake_time = 0.0
        self.assertFalse(self.assistant._is_wake_phrase("travis went to the store"))
        self.assertFalse(self.assistant._is_wake_phrase("the br rate was high"))
        self.assertFalse(self.assistant._is_wake_phrase("ask the assistant"))

    def test_embedded_command_extraction(self):
        cmd = self.assistant._extract_command_from_wake("hey jarvis open notepad")
        self.assertEqual(cmd, "open notepad")

        cmd2 = self.assistant._extract_command_from_wake("jarvis analyze my project")
        self.assertEqual(cmd2, "analyze my project")

        # Wake only returns empty string
        cmd3 = self.assistant._extract_command_from_wake("hey jarvis")
        self.assertEqual(cmd3, "")

    def test_prompt_refiner_technical_vocabulary(self):
        raw = "um jarvis research open claw and fast api using chroma db"
        res = refine_voice_prompt(raw)
        self.assertTrue(res["was_modified"])
        self.assertIn("OpenClaw", res["refined"])
        self.assertIn("FastAPI", res["refined"])
        self.assertIn("ChromaDB", res["refined"])
        self.assertEqual(res["confidence"], "HIGH_CONFIDENCE")

    def test_conversational_clarification_and_approval(self):
        # Set up a pending clarification question
        self.assistant._pending_clarification = {"goal": "create comparison report", "question": "DOCX or PDF?"}
        self.assistant.state_machine.transition_to(VoiceState.WAITING_APPROVAL, force=True)
        self.assistant.orchestrator.chat = lambda text: "Comparison report generated and verified."

        async def _test_approval():
            await self.assistant.process_command("yes proceed")

        asyncio.run(_test_approval())
        self.assertIsNone(self.assistant._pending_clarification)

    def test_conversational_cancellation(self):
        self.assistant._pending_clarification = {"goal": "delete files", "question": "Are you sure?"}
        self.assistant.state_machine.transition_to(VoiceState.WAITING_APPROVAL, force=True)
        self.assistant.orchestrator.chat = lambda text: "Deleted."

        async def _test_cancel():
            await self.assistant.process_command("cancel")

        asyncio.run(_test_cancel())
        self.assertIsNone(self.assistant._pending_clarification)


if __name__ == "__main__":
    unittest.main()
