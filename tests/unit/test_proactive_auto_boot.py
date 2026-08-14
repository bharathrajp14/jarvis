# tests/unit/test_proactive_auto_boot.py — Unit test for Proactive Listener Auto-Boot & Shutdown Hook
"""
Verifies auto-boot initialization and graceful shutdown signal handlers for Proactive Multi-Channel Listener.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from actions.proactive_listener import get_proactive_listener, ProactiveMultiChannelListener


class TestProactiveAutoBoot(unittest.TestCase):

    def setUp(self):
        self.listener = get_proactive_listener()

    def test_01_auto_boot_start_stop_cycle(self):
        """Verify listener can be started and stopped cleanly without throwing exceptions."""
        start_res = self.listener.start(poll_interval=10)
        self.assertIn("Listener", start_res)
        self.assertTrue(self.listener.running)

        status = self.listener.get_status()
        self.assertTrue(status["running"])
        self.assertEqual(status["poll_interval"], 10)

        stop_res = self.listener.stop()
        self.assertIn("stopped", stop_res)
        self.assertFalse(self.listener.running)


if __name__ == "__main__":
    unittest.main()
