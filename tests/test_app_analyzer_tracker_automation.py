# tests/test_app_analyzer_tracker_automation.py — Verification suite for App Analyzer, Tracker, and Automation Engine
"""
Automated unit and integration test suite verifying system application analysis,
start history tracking, background process watching, and general automation.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure root project path is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actions.app_analyzer import get_app_analyzer, SystemAppAnalyzer
from actions.app_tracker import get_app_tracker, log_app_launch
from watchers.app_launch_watcher import get_app_launch_watcher
from actions.automation_engine import get_automation_engine
from tools.registry import execute_tool, TOOL_REGISTRY, _import_plugins


class TestAppAnalyzerTrackerAutomation(unittest.TestCase):

    def setUp(self):
        _import_plugins()

    def test_01_installed_apps_scanning(self):
        """Test scanning installed applications on host OS."""
        analyzer = get_app_analyzer()
        installed = analyzer.scan_installed_apps()
        self.assertIsInstance(installed, list)
        print(f"\n[Test] Scanned {len(installed)} installed applications on system.")
        if installed:
            first_app = installed[0]
            self.assertIn("name", first_app)
            self.assertIn("path", first_app)
            self.assertIn("source", first_app)
            print(f"[Test] Sample installed app: {first_app['name']} ({first_app['source']})")

    def test_02_running_apps_inspection(self):
        """Test retrieving active processes and GUI windows."""
        analyzer = get_app_analyzer()
        running = analyzer.get_running_apps(filter_gui_only=True)
        self.assertIsInstance(running, list)
        self.assertGreater(len(running), 0)
        top_proc = running[0]
        self.assertIn("pid", top_proc)
        self.assertIn("name", top_proc)
        self.assertIn("memory_mb", top_proc)
        print(f"[Test] Retreived {len(running)} active running applications. Top app: PID {top_proc['pid']} {top_proc['name']} ({top_proc['memory_mb']} MB)")

    def test_03_app_search(self):
        """Test searching for applications by keyword."""
        analyzer = get_app_analyzer()
        res = analyzer.search_apps("cmd")
        self.assertIn("installed_matches", res)
        self.assertIn("running_matches", res)
        print(f"[Test] App search for 'cmd': {len(res['installed_matches'])} installed, {len(res['running_matches'])} running.")

    def test_04_app_launch_tracker(self):
        """Test persistent SQLite logging of app start events."""
        tracker = get_app_tracker()
        # Log synthetic test launch
        success = tracker.log_launch(
            app_name="TestAutomationApp",
            exe_path="C:\\Program Files\\TestApp\\test.exe",
            pid=99999,
            source="unit_test",
            details={"test": True}
        )
        self.assertTrue(success)

        history = tracker.get_history(limit=10, app_name="TestAutomationApp")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]["app_name"], "TestAutomationApp")
        self.assertEqual(history[0]["source"], "unit_test")
        print(f"[Test] Successfully logged and retrieved app launch record #{history[0]['id']} for '{history[0]['app_name']}'")

        stats = tracker.get_statistics()
        self.assertGreaterEqual(stats["total_launches"], 1)
        print(f"[Test] App launch telemetry stats: Total {stats['total_launches']} launches, {stats['unique_apps']} unique apps.")

    def test_05_app_launch_watcher(self):
        """Test process creation watcher warm-up and delta check."""
        watcher = get_app_launch_watcher()
        watcher.initialize_pids()
        self.assertTrue(watcher._initialized)
        new_launches = watcher.check_new_launches()
        self.assertIsInstance(new_launches, int)
        print(f"[Test] AppLaunchWatcher initialized with {len(watcher._known_pids)} active PIDs. New launches: {new_launches}")

    def test_06_automation_engine_workflow(self):
        """Test multi-step macro workflow script execution."""
        engine = get_automation_engine()
        steps = [
            {"action": "sleep", "seconds": 0.1},
            {"action": "shell", "command": "echo Automation Engine Verification Success"},
        ]
        res = engine.run_workflow_script(steps)
        self.assertTrue(res["success"])
        self.assertEqual(res["step_count"], 2)
        print(f"[Test] Workflow execution result: {res['results']}")

    def test_07_tool_registry_integration(self):
        """Test executing registered tools via registry."""
        tools_to_test = [
            "list_installed_applications",
            "list_running_applications",
            "search_applications",
            "get_app_launch_history",
            "get_app_usage_statistics",
            "run_automation_workflow",
            "execute_system_automation"
        ]
        for t_name in tools_to_test:
            self.assertIn(t_name, TOOL_REGISTRY)

        # Test execute_tool call
        out1 = execute_tool("list_installed_applications", {"limit": 5})
        self.assertNotIn("ERROR: Unknown tool", out1)
        print(f"[Test] Tool 'list_installed_applications' output snippet:\n{out1[:150]}...")

        out2 = execute_tool("get_app_usage_statistics", {})
        self.assertNotIn("ERROR: Unknown tool", out2)
        print(f"[Test] Tool 'get_app_usage_statistics' output snippet:\n{out2[:150]}...")

        out3 = execute_tool("execute_system_automation", {"command": "Write-Output 'Hello Jarvis'"})
        self.assertIn("Hello Jarvis", out3)
        print(f"[Test] Tool 'execute_system_automation' output:\n{out3}")


if __name__ == "__main__":
    unittest.main()
