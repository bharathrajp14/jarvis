# tests/unit/test_proactive_listener.py — Verification suite for Proactive Listener & Dispatcher
"""
Unit tests verifying multi-channel listener background execution, intent classification,
message deduplication, and user action approval workflow.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from actions.proactive_listener import get_proactive_listener, ProactiveMultiChannelListener
from actions.channel_action_dispatcher import get_channel_action_dispatcher, ChannelActionDispatcher
from tools.registry import execute_tool, TOOL_REGISTRY, _import_plugins


class TestProactiveListener(unittest.TestCase):

    def setUp(self):
        self.listener = get_proactive_listener()
        self.dispatcher = ChannelActionDispatcher(listener=self.listener)
        _import_plugins(full=True)

    def test_01_listener_singleton_and_status(self):
        """Test listener singleton instance and start/stop status."""
        status = self.listener.get_status()
        self.assertIn("running", status)
        self.assertIn("pending_action_count", status)

    def test_02_intent_classification(self):
        """Test classification of meeting requests, action required, and inquiries."""
        intent, entities = self.listener._classify_message("Let's schedule a meeting tomorrow at 3:00 PM to review project.")
        self.assertEqual(intent, "MEETING_REQUEST")
        self.assertIn("time", entities)

        intent_urgent, _ = self.listener._classify_message("URGENT: Please send the updated report ASAP.")
        self.assertEqual(intent_urgent, "ACTION_REQUIRED")

        intent_inquiry, _ = self.listener._classify_message("What time does the conference start?")
        self.assertEqual(intent_inquiry, "INQUIRY")

    def test_03_action_dispatcher_dismiss(self):
        """Test user decision 'dismiss' on pending action item."""
        test_item = {
            "id": "test_msg_999",
            "channel": "EMAIL",
            "sender": "alex@example.com",
            "snippet": "Test email snippet",
            "intent": "INFORMATIONAL",
            "entities": {}
        }
        self.listener.pending_actions.append(test_item)

        res = self.dispatcher.process_user_decision("test_msg_999", "dismiss")
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "dismissed")

    def test_04_proactive_tools_registry(self):
        """Test tool registry execution for proactive listener tools."""
        self.assertIn("start_multichannel_listener", TOOL_REGISTRY)
        self.assertIn("stop_multichannel_listener", TOOL_REGISTRY)
        self.assertIn("get_pending_channel_actions", TOOL_REGISTRY)
        self.assertIn("respond_channel_action", TOOL_REGISTRY)

        out = execute_tool("get_pending_channel_actions", {})
        self.assertIn("pending_actions", out)


if __name__ == "__main__":
    unittest.main()
