# tests/unit/test_stage_decomposer.py — Unit Tests for StageDecomposer and StageExecutionEngine
from __future__ import annotations

import unittest
from agent.stage_decomposer import (
    StageDecomposer,
    StageExecutionEngine,
    StageCapability,
    ExecutionStage,
)


class TestStageDecomposer(unittest.TestCase):

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

    def test_composite_task_detection(self):
        # 1. Complex master prompt is identified as composite
        self.assertTrue(StageDecomposer.is_composite_task(self.master_prompt))

        # 2. Simple single-turn query is NOT composite
        self.assertFalse(StageDecomposer.is_composite_task("What is the capital of France?"))
        self.assertFalse(StageDecomposer.is_composite_task("Open Chrome"))
        self.assertFalse(StageDecomposer.is_composite_task("Mute volume"))

    def test_stage_decomposition_structure(self):
        stages = StageDecomposer.decompose(self.master_prompt, parent_task_id="task_test_123")
        self.assertGreaterEqual(len(stages), 8)

        capabilities = [s.capability for s in stages]
        self.assertIn(StageCapability.SYSTEM_DIAGNOSTICS, capabilities)
        self.assertIn(StageCapability.VISION_SCREEN_CAPTURE, capabilities)
        self.assertIn(StageCapability.WEB_RESEARCH, capabilities)
        self.assertIn(StageCapability.REASONING_ANALYSIS, capabilities)
        self.assertIn(StageCapability.DOC_CODE_GENERATION, capabilities)
        self.assertIn(StageCapability.ARTIFACT_EXPORT, capabilities)
        self.assertIn(StageCapability.BROWSER_INTERACTION, capabilities)
        self.assertIn(StageCapability.ACTION_VERIFICATION, capabilities)
        self.assertIn(StageCapability.MEMORY_UPDATE, capabilities)
        self.assertIn(StageCapability.SPOKEN_SUMMARY, capabilities)

    def test_deterministic_vs_model_stage_classification(self):
        stages = StageDecomposer.decompose(self.master_prompt)
        for s in stages:
            if s.capability in (StageCapability.SYSTEM_DIAGNOSTICS, StageCapability.ARTIFACT_EXPORT, StageCapability.ACTION_VERIFICATION, StageCapability.MEMORY_UPDATE):
                self.assertTrue(s.is_deterministic, f"Stage {s.name} should be deterministic")

    def test_stage_execution_engine(self):
        stages = StageDecomposer.decompose(self.master_prompt)
        engine = StageExecutionEngine()
        context = engine.execute_stages(stages, self.master_prompt)

        self.assertIn("stage_results", context)
        self.assertIn("diagnostics", context["stage_results"])
        self.assertIn("comparison", context["stage_results"])
        self.assertIn("spoken_summary", context)
        self.assertGreaterEqual(len(context["verified_operations"]), 6)
        self.assertEqual(len(context["failed_operations"]), 0)

        # Spoken summary must address user as 'Sir' and summarize verified operations
        summary = context["spoken_summary"]
        self.assertIn("Sir", summary)
        self.assertIn("verified", summary.lower())


if __name__ == "__main__":
    unittest.main()
