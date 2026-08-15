# tests/e2e/test_master_task_lifecycle.py — E2E Master Multimodal Task Lifecycle & Stage Verification Test
from __future__ import annotations

import unittest
from pathlib import Path
from core.bootstrap import build_assistant_runtime
from agent.artifacts import get_artifact_manager


class TestMasterTaskLifecycle(unittest.TestCase):

    def setUp(self):
        self.master_prompt = (
            "Jarvis, I want you to perform a complete system and AI capability audit. "
            "First, check my CPU, RAM, disk space, battery status, running applications, and available audio devices. "
            "Then take a screenshot of my current screen and analyze what is visible, including the active browser and any errors or warnings. "
            "Open Microsoft Edge, search for BR JARVIS on GitHub, inspect the most relevant result, and tell me what you find. "
            "Then search for Microsoft JARVIS/HuggingGPT and compare its architecture with BR JARVIS. "
            "After that, create a professional HTML report containing the system diagnostics, detected audio devices, screenshots/visual findings, BR JARVIS findings, and the architecture comparison. "
            "Save the report as a user-accessible artifact, not only inside your sandbox. "
            "Verify that the file actually exists and that its contents are readable. "
            "Open the generated report in the browser, take a screenshot of the rendered page, analyze the screenshot, and verify that the report loaded correctly without any browser error. "
            "If you find a problem anywhere, don't just report that the operation succeeded—diagnose the problem, fix it, retry the affected step, and verify the result again. "
            "Then give me a concise spoken summary of everything you discovered, including which operations were successfully verified, which failed, and how you recovered from any failures. "
            "Finally, remember that today I am testing BR JARVIS and call me Sir in future conversations."
        )

    def test_end_to_end_master_audit_execution(self):
        runtime = build_assistant_runtime()
        response = runtime.orchestrator.chat(self.master_prompt)

        # 1. Assert response is not an unhandled backend failure
        self.assertNotIn("All backends failed", response)
        self.assertNotIn("TASK_EXECUTION_FAILED", response)

        # 2. Assert response contains spoken summary addressing user as Sir
        self.assertIn("Sir", response)
        self.assertIn("audit", response.lower())

        # 3. Assert HTML artifact was exported to verified host location
        mgr = get_artifact_manager()
        report_file = mgr.get_host_artifact_dir() / "JARVIS_System_and_Architecture_Audit.html"
        self.assertTrue(report_file.exists(), f"Expected artifact {report_file} to exist on host")
        content = report_file.read_text(encoding="utf-8")
        self.assertIn("BR JARVIS", content)
        self.assertIn("System & Hardware Diagnostics", content)
        self.assertIn("Architecture Comparison", content)


if __name__ == "__main__":
    unittest.main()
