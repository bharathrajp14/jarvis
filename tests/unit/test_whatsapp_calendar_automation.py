# tests/test_whatsapp_calendar_automation.py — Automated verification suite for WhatsApp and Calendar Engine
"""
Automated unit & integration test suite verifying WhatsApp contact messaging,
scheduled messaging queues, natural language calendar task creation, searching,
reminders, and tool execution via registry.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure root project path is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actions.whatsapp_automation import get_whatsapp_automation
from actions.calendar_engine import get_calendar_engine
from actions.automation_engine import get_automation_engine
import logging
logger = logging.getLogger("TestWhatsAppCalendar")

from tools.registry import execute_tool, TOOL_REGISTRY, _import_plugins



class TestWhatsAppCalendarAutomation(unittest.TestCase):

    def setUp(self):
        _import_plugins()

    def test_01_whatsapp_contacts_and_recipient_resolution(self):
        """Test contact saving and recipient resolution."""
        wa = get_whatsapp_automation()
        add_res = wa.add_contact("Alice Smith", "+15551234567")
        self.assertIn("Saved contact", add_res)

        name, phone = wa.resolve_recipient("Alice")
        self.assertEqual(phone, "+15551234567")
        logger.info(f"\n[Test] WhatsApp contact resolution: 'Alice' -> '{name}' ({phone})")

    def test_02_whatsapp_messaging_and_scheduling(self):
        """Test formatting and scheduling WhatsApp messages."""
        wa = get_whatsapp_automation()
        res = wa.send_message("+15551234567", "Hello from BR-Jarvis Automated Test!", open_browser=True)
        self.assertTrue("Opened" in res or "sent" in res.lower() or "WhatsApp" in res)

        sched_res = wa.schedule_message("Alice", "Scheduled Reminder", "23:59:59")
        self.assertIn("Scheduled WhatsApp message", sched_res)
        logger.info(f"[Test] WhatsApp schedule output: {sched_res}")

    def test_03_calendar_natural_language_event_creation(self):
        """Test creating calendar events with natural language expressions."""
        cal = get_calendar_engine()
        event_res = cal.create_event(
            title="Team Sync & Review",
            start_time_str="tomorrow 3pm",
            description="Discuss MK37 updates",
            location="Room 404 / Google Meet",
            attendees=["Alice"]
        )
        self.assertTrue(event_res["success"])
        self.assertIn("Team Sync & Review", event_res["title"])
        logger.info(f"[Test] Calendar Event Created: #{event_res['event_id']} '{event_res['title']}' on {event_res['start_time']}")

    def test_04_calendar_listing_and_searching(self):
        """Test listing and searching calendar events."""
        cal = get_calendar_engine()
        events = cal.list_events(days=7)
        self.assertGreater(len(events), 0)

        search_matches = cal.search_events("Sync")
        self.assertGreater(len(search_matches), 0)
        self.assertEqual(search_matches[0]["title"], "Team Sync & Review")
        logger.info(f"[Test] Calendar Search for 'Sync' found {len(search_matches)} matches.")

    def test_05_workflow_integration_whatsapp_calendar(self):
        """Test multi-step macro workflow execution with WhatsApp and Calendar steps."""
        engine = get_automation_engine()
        steps = [
            {
                "action": "calendar",
                "title": "Automated Project Audit",
                "start_time": "in 1 hour",
                "location": "Virtual Office"
            },
            {
                "action": "whatsapp",
                "recipient": "Alice",
                "message": "Hey Alice, project audit is scheduled in 1 hour."
            }
        ]
        res = engine.run_workflow_script(steps)
        self.assertTrue(res["success"])
        self.assertEqual(res["step_count"], 2)
        logger.info(f"[Test] Workflow script execution output: {res['results']}")

    def test_06_tool_registry_execution(self):
        """Test executing WhatsApp and Calendar tools via tool registry."""
        from tools.registry import _import_plugins
        _import_plugins(full=True)
        tools_to_test = [

            "send_whatsapp",
            "schedule_whatsapp_message",
            "manage_whatsapp_contacts",
            "create_calendar_event",
            "list_calendar_events",
            "search_calendar_events",
            "delete_calendar_event"
        ]
        for t_name in tools_to_test:
            self.assertIn(t_name, TOOL_REGISTRY)

        out_contact = execute_tool("manage_whatsapp_contacts", {"action": "list"})
        self.assertIn("Alice", out_contact)

        out_cal = execute_tool("list_calendar_events", {"days": 7})
        self.assertIn("Team Sync & Review", out_cal)
        logger.info(f"[Test] Tool 'list_calendar_events' output:\n{out_cal}")


if __name__ == "__main__":
    unittest.main()
