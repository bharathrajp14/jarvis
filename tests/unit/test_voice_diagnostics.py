# tests/unit/test_voice_diagnostics.py — Unit Tests for Voice Self-Diagnostics
from __future__ import annotations

import asyncio
import unittest
from voice.assistant import BRVoiceAssistant


class TestVoiceDiagnostics(unittest.TestCase):

    def test_run_voice_diagnostics(self):
        assistant = BRVoiceAssistant(ui=None)

        async def _run():
            res = await assistant.run_voice_diagnostics()
            return res

        report = asyncio.run(_run())
        self.assertIsInstance(report, str)
        self.assertIn("Voice diagnostics completed", report)


if __name__ == "__main__":
    unittest.main()
