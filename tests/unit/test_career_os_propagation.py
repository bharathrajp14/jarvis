# tests/unit/test_career_os_propagation.py — Cross-Layer Career OS Propagation Test Suite
from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch

from core.config import get_config, JarvisConfig, CareerConfig
from security.policy_engine import DESTRUCTIVE_TOOLS, ALWAYS_ALLOWED_SAFE, PolicyEngine, PermissionMode
from tools.registry import TOOL_REGISTRY, get_pruned_tool_prompt_block, execute_tool
from core.terminal.session import TerminalSession
from core.terminal.commands import SlashCommandHandler


def test_config_career_propagation():
    """Verify CareerConfig is loaded into JarvisConfig with appropriate defaults and env parsing."""
    os.environ["JARVIS_CAREER_TRACKER_PATH"] = "Test_Tracker.xlsx"
    os.environ["JARVIS_CAREER_EMAIL_SYNC_HOURS"] = "48"
    os.environ["JARVIS_CAREER_MATCH_THRESHOLD"] = "0.75"
    
    cfg = JarvisConfig.load()
    assert isinstance(cfg.career, CareerConfig)
    assert cfg.career.tracker_path == "Test_Tracker.xlsx"
    assert cfg.career.email_sync_hours == 48
    assert cfg.career.match_threshold == 0.75
    assert cfg.career.auto_confirm_offer is False


def test_tool_registry_career_propagation():
    """Verify tool registry includes career tools and lazy loads them on career queries."""
    prompt_block = get_pruned_tool_prompt_block(user_prompt="I need to apply for a software engineering job and tailor my resume")
    assert "career_resume_tailor" in prompt_block or "career_job_search" in prompt_block

    # Test direct execution lookup
    res = execute_tool("career_profile_get", {})
    assert "Bharath" in str(res) or "contact" in str(res) or "success" in str(res).lower()


def test_policy_engine_career_propagation():
    """Verify policy engine correctly tiers career actions into destructive vs safe."""
    assert "career_application_submit" in DESTRUCTIVE_TOOLS
    assert "career_offer_confirm" in DESTRUCTIVE_TOOLS
    assert "career_spreadsheet_sync" in DESTRUCTIVE_TOOLS
    
    assert "career_profile_get" in ALWAYS_ALLOWED_SAFE
    assert "career_job_search" in ALWAYS_ALLOWED_SAFE
    assert "career_ats_evaluate" in ALWAYS_ALLOWED_SAFE
    assert "career_analytics_report" in ALWAYS_ALLOWED_SAFE


def test_cli_commands_career_propagation():
    """Verify CLI command handler dispatches all Career OS subcommands cleanly."""
    session = TerminalSession(mode="career")
    cmd = SlashCommandHandler(session)
    
    # Test executing career overview
    res_career = cmd.execute("/career")
    assert res_career is True

    # Test executing career analytics
    res_analytics = cmd.execute("/career analytics")
    assert res_analytics is True

    # Test executing applications list
    res_apps = cmd.execute("/applications")
    assert res_apps is True

    # Test executing interviews list
    res_iv = cmd.execute("/interviews")
    assert res_iv is True

    # Test executing offers list
    res_off = cmd.execute("/offers")
    assert res_off is True

    # Test executing emails log
    res_em = cmd.execute("/emails")
    assert res_em is True


def test_start_and_brjarvis_career_propagation():
    """Verify start.py and brjarvis.py expose Career OS routes and mode maps."""
    import start
    assert hasattr(start, "launch_career_studio")
    assert hasattr(start, "launch_career_sync")
    assert hasattr(start, "doctor")

    import brjarvis
    assert hasattr(brjarvis, "main")


def test_doctor_diagnostics_career_propagation():
    """Verify doctor function runs all diagnostic phases without unhandled exceptions."""
    from start import doctor
    # Run in auto_confirm mode to avoid interactive prompts
    try:
        doctor(auto_confirm=True)
        assert True
    except Exception as e:
        pytest.fail(f"Doctor diagnostic run raised unexpected error: {e}")
