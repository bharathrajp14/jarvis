# tests/test_master_suite.py — Unified Master Test Suite Runner for BR JARVIS MK37
"""
Master Test Suite Runner consolidating all 80+ unit & integration tests across 5 major domains:
1. Antigravity Agent Core (Scratchpad, Planning, Artifacts, Transcripts, Step Planner)
2. Voice & Acoustic Pipeline (VoicePromptRefiner, Vocal Filler Cleaner, Vocab Mapper)
3. UI & Multi-Task Dashboard (Glossy Task Cards, Progress Bars, Canvas HUD)
4. System Resiliency & OS Control (WorkingMemory Goal Pinning, PyAutoGUI Failsafe, Multi-Backend Clipboard)
5. Core Subsystems & Vision (Core Runtime, Context Engine, Guardian, Semantic Vision)
"""
from __future__ import annotations

import unittest
import pytest
import sys
from pathlib import Path


def run_master_suite() -> int:
    """Run master test suite across all sub-domains using Pytest runner."""
    project_root = Path(__file__).resolve().parent.parent
    test_dir = project_root / "tests"
    
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    if 'logger' in globals() or 'logger' in locals():
        logger.info("BR JARVIS -- MASTER SYSTEM TEST SUITE RUNNER")
    else:
        import logging
        logging.getLogger(__name__).info("BR JARVIS -- MASTER SYSTEM TEST SUITE RUNNER")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)

    exit_code = pytest.main([
        str(test_dir),
        "-v",
        "--tb=short",
        "-W", "ignore::DeprecationWarning"
    ])
    return exit_code


class TestMasterSuiteRunner(unittest.TestCase):
    """Pytest-compatible Master Suite class wrapper."""

    def test_all_system_components(self):
        root = Path(__file__).resolve().parent.parent
        # When executed directly as script, run pytest.main
        # Avoid nested pytest session invocation if already running within pytest
        if "pytest" in sys.modules and any("pytest" in arg for arg in sys.argv):
            # Verify root modules can be imported cleanly
            import core.intent_engine
            import permissions
            self.assertTrue(hasattr(permissions, "PermissionPolicy"))
            return

        res = pytest.main([
            str(root / "tests" / "unit" / "test_step_planner.py"),
            str(root / "tests" / "unit" / "test_ui_multitask.py"),
            str(root / "tests" / "unit" / "test_voice_pipeline.py"),
            str(root / "tests" / "unit" / "test_antigravity_system.py"),
            str(root / "tests" / "unit" / "test_regression_fixes.py"),
            str(root / "tests" / "unit" / "test_clipboard_read.py"),
            "-W", "ignore::DeprecationWarning"
        ])
        self.assertEqual(res, 0, "Master system component verification failed")


if __name__ == "__main__":
    sys.exit(run_master_suite())
