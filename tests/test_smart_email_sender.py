# tests/test_smart_email_sender.py — Verification suite for Smart Email Creation & Sending Engine
"""
Automated unit & integration test suite verifying smart email composition, recipient resolution,
contact storage, scheduled emails, and tool execution via registry.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure root project path is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actions.smart_email_sender import get_smart_email_sender
from actions.automation_engine import get_automation_engine
from tools.registry import execute_tool, TOOL_REGISTRY, _import_plugins


class TestSmartEmailSender(unittest.TestCase):

    def setUp(self):
        _import_plugins()
        self.sender = get_smart_email_sender()

    def test_01_contact_saving_and_resolution(self):
        """Test saving email contact and recipient resolution."""
        add_res = self.sender.add_contact("Manager Alex", "alex.manager@company.com")
        self.assertIn("Saved email contact", add_res)

        name, email_addr = self.sender.resolve_recipient("Manager Alex")
        self.assertEqual(email_addr, "alex.manager@company.com")

        # Test partial match
        name2, email2 = self.sender.resolve_recipient("Alex")
        self.assertEqual(email2, "alex.manager@company.com")
        print(f"\n[Test] Email contact resolution: 'Alex' -> '{name2}' ({email2})")

    def test_02_send_email_draft_and_fallback(self):
        """Test sending email with browser draft fallback."""
        res = self.sender.send_email(
            recipient="alex.manager@company.com",
            subject="Project Architecture Update",
            body="Hi Alex, please find the latest architecture update attached.",
            open_fallback=False
        )
        self.assertTrue("Drafted email" in res or "sent" in res.lower())
        print(f"[Test] send_email output snippet: {res[:100]}...")

    def test_03_schedule_email(self):
        """Test scheduling an email for future delivery."""
        sched_res = self.sender.schedule_email(
            recipient="alex.manager@company.com",
            subject="Weekly Progress Report",
            body="Here is the weekly report.",
            send_at="23:59:59"
        )
        self.assertIn("Scheduled email to", sched_res)
        print(f"[Test] Scheduled email output: {sched_res}")

    def test_04_workflow_integration(self):
        """Test multi-step macro workflow execution containing email step."""
        engine = get_automation_engine()
        steps = [
            {
                "action": "send_email",
                "recipient": "alex.manager@company.com",
                "subject": "Automated Status Alert",
                "body": "System check complete."
            }
        ]
        res = engine.run_workflow_script(steps)
        self.assertTrue(res["success"])
        self.assertEqual(res["step_count"], 1)
        print(f"[Test] Workflow execution with email step: {res['results']}")

    def test_05_tool_registry_execution(self):
        """Test executing smart email tools via tool registry."""
        tools_to_test = ["send_email", "schedule_email", "manage_email_contacts"]
        for t_name in tools_to_test:
            self.assertIn(t_name, TOOL_REGISTRY)

        out_contacts = execute_tool("manage_email_contacts", {"action": "list"})
        self.assertIn("Alex", out_contacts)
        print(f"[Test] Tool 'manage_email_contacts' output:\n{out_contacts}")


if __name__ == "__main__":
    unittest.main()
