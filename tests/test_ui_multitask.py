# tests/test_ui_multitask.py — Unit tests for UI Multi-Tasking & Sub-Agent Dashboard
from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from ui import JarvisUI


class TestUIMultiTask(unittest.TestCase):

    def setUp(self):
        # Create lightweight dummy UI object without opening window
        self.ui = MagicMock(spec=JarvisUI)
        self.ui._agent_tasks = {}

        # Bind methods directly from JarvisUI
        self.ui.update_agent_task = JarvisUI.update_agent_task.__get__(self.ui, JarvisUI)
        self.ui.remove_agent_task = JarvisUI.remove_agent_task.__get__(self.ui, JarvisUI)
        self.ui.clear_agent_tasks = JarvisUI.clear_agent_tasks.__get__(self.ui, JarvisUI)
        self.ui.root = MagicMock()

    def test_update_agent_task(self):
        self.ui.update_agent_task("task_001", "Check System RAM", "running", progress=0.45, result="Checking memory...")
        
        self.assertIn("task_001", self.ui._agent_tasks)
        info = self.ui._agent_tasks["task_001"]
        self.assertEqual(info["name"], "Check System RAM")
        self.assertEqual(info["status"], "running")
        self.assertEqual(info["progress"], 0.45)
        self.assertEqual(info["result"], "Checking memory...")

    def test_task_status_transition(self):
        self.ui.update_agent_task("task_002", "Deploy Container", "queued")
        self.assertEqual(self.ui._agent_tasks["task_002"]["status"], "queued")

        self.ui.update_agent_task("task_002", "Deploy Container", "completed", progress=1.0, result="Container live")
        self.assertEqual(self.ui._agent_tasks["task_002"]["status"], "completed")
        self.assertEqual(self.ui._agent_tasks["task_002"]["progress"], 1.0)

    def test_remove_and_clear_tasks(self):
        self.ui.update_agent_task("task_003", "Task A", "running")
        self.ui.update_agent_task("task_004", "Task B", "running")

        self.ui.remove_agent_task("task_003")
        self.assertNotIn("task_003", self.ui._agent_tasks)
        self.assertIn("task_004", self.ui._agent_tasks)

        self.ui.clear_agent_tasks()
        self.assertEqual(len(self.ui._agent_tasks), 0)


if __name__ == "__main__":
    unittest.main()
