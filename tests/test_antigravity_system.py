# tests/test_antigravity_system.py — Unit tests for Scratchpad, Planning Mode, Artifacts & Transcripts
from __future__ import annotations

import unittest
from pathlib import Path
from agent.scratchpad import get_scratchpad
from tools.scratchpad_tools import (
    tool_scratchpad_write,
    tool_scratchpad_read,
    tool_scratchpad_eval,
    tool_scratchpad_list,
    tool_scratchpad_clear,
)
from agent.planning_mode import get_planning_engine
from agent.artifacts import ArtifactDocument, ArtifactMetadata, make_file_link
from agent.transcript_logger import get_transcript_logger


class TestAntigravitySystem(unittest.TestCase):

    def setUp(self):
        self.sp = get_scratchpad()
        self.sp.clear()

    def test_scratchpad_operations(self):
        # Write
        w_res = tool_scratchpad_write({"name": "test_unit.py", "content": "print('hello from scratchpad')"[:100]})
        self.assertIn("Scratchpad file created", w_res)

        # Read
        r_res = tool_scratchpad_read({"name": "test_unit.py"})
        self.assertEqual(r_res, "print('hello from scratchpad')")

        # Eval
        e_res = tool_scratchpad_eval({"script": "print('eval success 123')", "language": "python"})
        self.assertIn("eval success 123", e_res)

        # List
        l_res = tool_scratchpad_list({})
        self.assertIn("test_unit.py", l_res)

        # Clear
        c_res = tool_scratchpad_clear({})
        self.assertIn("Scratchpad cleared", c_res)

    def test_planning_engine(self):
        pe = get_planning_engine()

        # Warrants plan evaluation
        warrants, reason = pe.warrants_plan("implement scratchpad and planning mode in repository")
        self.assertTrue(warrants)

        warrants_simple, _ = pe.warrants_plan("read clipboard")
        self.assertFalse(warrants_simple)

        # Generate implementation plan
        plan_path = pe.generate_implementation_plan(
            goal="Test Plan Feature",
            proposed_changes=[{
                "component": "Test Component",
                "files": [{"tag": "NEW", "path": "agent/scratchpad.py", "description": "Scratchpad engine"}]
            }],
            verification_steps=["pytest tests/test_antigravity_system.py"]
        )
        self.assertTrue(plan_path.exists())
        plan_content = plan_path.read_text(encoding="utf-8")
        self.assertIn("Test Plan Feature", plan_content)
        self.assertIn("Verification Plan", plan_content)

        # Generate walkthrough
        wt_path = pe.generate_walkthrough(
            goal="Test Plan Feature",
            accomplishments=["Created test features", "Passed unit tests"],
        )
        self.assertTrue(wt_path.exists())
        wt_content = wt_path.read_text(encoding="utf-8")
        self.assertIn("Accomplishments", wt_content)

    def test_artifacts_formatting(self):
        doc = ArtifactDocument("Sample Artifact", Path("scratch/test_art.md"))
        doc.add_alert("IMPORTANT", "Critical alert test message")
        doc.add_mermaid_diagram("graph TD\nA-->B")

        rendered = doc.render()
        self.assertIn("# Sample Artifact", rendered)
        self.assertIn("> [!IMPORTANT]", rendered)
        self.assertIn("```mermaid", rendered)

        link = make_file_link("agent/scratchpad.py", start_line=10, end_line=20)
        self.assertIn("file:///", link)
        self.assertIn("#L10-L20", link)

    def test_transcript_logger(self):
        logger = get_transcript_logger("test_session_123")
        logger.log_step(
            source="USER_EXPLICIT",
            step_type="USER_INPUT",
            content="Testing transcript logger step",
        )
        self.assertTrue(logger.compact_file.exists())
        self.assertTrue(logger.full_file.exists())


if __name__ == "__main__":
    unittest.main()
