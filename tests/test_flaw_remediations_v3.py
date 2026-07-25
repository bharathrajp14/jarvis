# tests/test_flaw_remediations_v3.py — Verification test suite for multi-subsystem flaw remediations
from __future__ import annotations

import unittest
import speech_recognition as sr
from memory.working import WorkingMemory
from watchers.file_watcher import FileWatcher
from watchers.system_watcher import SystemWatcher
from voice.assistant import BRVoiceAssistant


class TestFlawRemediationsV3(unittest.TestCase):

    def test_working_memory_trim_no_infinite_loop(self):
        """Verify WorkingMemory._trim does not freeze in infinite loop when root prompt exceeds max_tokens."""
        wm = WorkingMemory(max_tokens=50)  # Very small budget (200 chars)
        huge_root = "A" * 1000  # 1000 chars = 250 tokens > 50 max_tokens
        wm.add("user", huge_root)
        wm.add("assistant", "Response 1")
        wm.add("user", "Follow up 1")

        # Must execute quickly without hanging in while loop
        wm._trim()
        self.assertLessEqual(len(wm.get()[0]["content"]) / 4, 60)

    def test_file_watcher_deleted_file_cleanup(self):
        """Verify FileWatcher removes deleted files from _file_mtimes to prevent memory leaks."""
        fw = FileWatcher()
        fw._file_mtimes["/dummy/path/obsolete.py"] = 12345.0
        fw.scan_for_changes()
        self.assertNotIn("/dummy/path/obsolete.py", fw._file_mtimes)

    def test_system_watcher_telemetry_check(self):
        """Verify SystemWatcher.check_telemetry executes without throwing unhandled exceptions."""
        sw = SystemWatcher()
        res = sw.check_telemetry()
        self.assertIn("status", res)

    def test_voice_assistant_energy_floor(self):
        """Verify VoiceAssistant enforces energy_threshold minimum floor of 200 RMS."""
        assistant = BRVoiceAssistant(ui=None)
        r = sr.Recognizer()
        r.energy_threshold = 50  # Set below minimum floor
        assistant._tune_recognizer(r)
        self.assertGreaterEqual(r.energy_threshold, 200)


if __name__ == "__main__":
    unittest.main()
