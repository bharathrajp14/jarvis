# tests/unit/test_cli_terminal.py — Test Suite for BR JARVIS CLI Agent Experience
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from core.terminal.theme import (
    Glyphs,
    MODE_COLORS,
    get_terminal_theme,
    COLOR_CYAN,
    COLOR_GREEN,
)
from core.terminal.renderer import TerminalRenderer
from core.terminal.commands import SlashCommandHandler, VALID_MODES
from core.terminal.session import TerminalSession
from core.terminal import run_query, run_cli
from core.cli import main as cli_main


@pytest.fixture
def mock_runtime():
    """Create a mock ApplicationRuntime with an orchestrator."""
    runtime = MagicMock()
    runtime.config.assistant.name = "BR JARVIS"
    runtime.config.models.default_backend = "Gemini"
    
    orch = MagicMock()
    orch.current_mode = "general"
    orch.session_id = "test-session-1234"
    orch.chat.return_value = "I am BR JARVIS, your cognitive agent."
    orch.working_memory.get.return_value = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Greetings."},
    ]
    orch.consolidate_on_exit.return_value = "Saved 2 memories."
    
    runtime.orchestrator = orch
    runtime.event_bus = MagicMock()
    return runtime


class TestTerminalTheme:
    """Test theme tokens, glyphs, and palette configuration."""

    def test_theme_generation(self):
        theme = get_terminal_theme()
        assert theme is not None
        assert "jarvis.primary" in theme.styles
        assert "tool.name" in theme.styles
        assert "verify.pass" in theme.styles

    def test_mode_colors(self):
        assert "general" in MODE_COLORS
        assert "coder" in MODE_COLORS
        assert "analyst" in MODE_COLORS
        assert MODE_COLORS["coder"] == COLOR_GREEN

    def test_glyphs(self):
        assert Glyphs.LIGHTNING == "⚡"
        assert Glyphs.SHIELD == "🛡️"
        assert Glyphs.CHECK == "✓"
        assert Glyphs.CROSS == "✗"
        badge = Glyphs.get_mode_badge("coder")
        assert "CODER" in badge


class TestTerminalRenderer:
    """Test renderer visual output components."""

    @pytest.fixture
    def renderer(self):
        return TerminalRenderer()

    def test_render_header(self, renderer):
        info = {
            "mode": "coder",
            "model": "Gemini 2.5 Flash",
            "session_id": "sess-test-999",
            "permission_mode": "FAIL-CLOSED",
            "memory_status": "ACTIVE",
        }
        # Should execute without exceptions
        renderer.render_header(info)

    def test_render_welcome(self, renderer):
        renderer.render_welcome()

    def test_render_tool_call_success(self, renderer):
        renderer.render_tool_call(
            tool_name="file_read",
            args={"path": "src/main.py"},
            result="print('hello')",
            status="COMPLETED",
            duration_ms=15.5,
            verified=True,
            evidence="File verified on disk",
        )

    def test_render_tool_call_failure(self, renderer):
        renderer.render_tool_call(
            tool_name="run_code",
            args={"code": "1/0"},
            result="ZeroDivisionError",
            status="FAILED",
            duration_ms=5.0,
            verified=False,
        )

    def test_render_verification(self, renderer):
        result_mock = MagicMock()
        result_mock.verified = True
        result_mock.status = "SUCCESS_VERIFIED"
        result_mock.evidence = "Artifact generated and hash matched."
        result_mock.error = None
        renderer.render_verification(result_mock)

    def test_render_diff(self, renderer):
        old_text = "def hello():\n    return 'old'\n"
        new_text = "def hello():\n    return 'new'\n"
        renderer.render_diff("test.py", old_text, new_text)

    def test_render_stage_progress(self, renderer):
        stages = [
            {"name": "Stage 1", "goal": "Analyze codebase", "agent_type": "recon"},
            {"name": "Stage 2", "goal": "Refactor module", "agent_type": "coder"},
            {"name": "Stage 3", "goal": "Run unit tests", "agent_type": "qa"},
        ]
        renderer.render_stage_progress(stages, current_idx=2, total_stages=3)

    def test_render_memory_card(self, renderer):
        memories = [
            {"type": "preference", "name": "editor", "content": "User prefers VS Code."},
            {"type": "operational", "name": "test_cmd", "content": "Use pytest for tests."},
        ]
        renderer.render_memory_card(memories)

    def test_render_tables(self, renderer):
        renderer.render_status_table({"Engine": "Active", "Version": "v40.2"})
        renderer.render_tasks_table([{"task_id": "t1", "goal": "Sample goal", "status": "completed", "current_step": 1, "total_steps": 1}])
        renderer.render_tools_table([{"name": "web_search", "description": "Search web", "category": "Web", "risk_level": "LOW"}])

    def test_render_markdown_and_error(self, renderer):
        renderer.render_markdown("### Agent Answer\nHere is code:\n```python\nprint(1)\n```")
        renderer.render_error("Test Error", "An error occurred", ["Try again", "Check config"])


class TestSlashCommandHandler:
    """Test interactive slash commands execution."""

    @pytest.fixture
    def session(self, mock_runtime):
        return TerminalSession(runtime=mock_runtime, auto_welcome=False)

    def test_help_command(self, session):
        res = session.commands.execute("/help")
        assert res is True

    def test_status_command(self, session):
        res = session.commands.execute("/status")
        assert res is True

    def test_mode_switch(self, session):
        res = session.commands.execute("/mode coder")
        assert res is True
        assert session.current_mode == "coder"
        assert session.orchestrator.current_mode == "coder"

    def test_mode_invalid(self, session):
        res = session.commands.execute("/mode unknown_mode_xyz")
        assert res is True
        assert session.current_mode != "unknown_mode_xyz"

    def test_model_command(self, session):
        res = session.commands.execute("/model claude")
        assert res is True

    def test_tasks_command(self, session):
        res = session.commands.execute("/tasks")
        assert res is True

    def test_memory_commands(self, session):
        assert session.commands.execute("/memory") is True
        assert session.commands.execute("/memory stats") is True
        assert session.commands.execute("/memory recent") is True
        assert session.commands.execute("/memory search test") is True

    def test_tools_command(self, session):
        assert session.commands.execute("/tools") is True
        assert session.commands.execute("/tools file") is True

    def test_plan_command(self, session):
        assert session.commands.execute("/plan Write a quicksort in Python") is True

    def test_verify_command(self, session):
        assert session.commands.execute("/verify") is True

    def test_compact_command(self, session):
        assert session.commands.execute("/compact") is True

    def test_version_command(self, session):
        assert session.commands.execute("/version") is True

    def test_clear_command(self, session):
        assert session.commands.execute("/clear") is True

    def test_quit_command(self, session):
        res = session.commands.execute("/quit")
        assert res is False


class TestTerminalSessionExecution:
    """Test TerminalSession execution turns and one-shot queries."""

    def test_one_shot_query(self, mock_runtime):
        session = TerminalSession(runtime=mock_runtime, auto_welcome=False)
        ret = session.run_query("What is BR JARVIS?")
        assert ret == 0
        mock_runtime.orchestrator.chat.assert_called_with("What is BR JARVIS?")

    def test_execute_turn_interrupt(self, mock_runtime):
        mock_runtime.orchestrator.chat.side_effect = KeyboardInterrupt()
        session = TerminalSession(runtime=mock_runtime, auto_welcome=False)
        # Should gracefully catch KeyboardInterrupt without crashing
        session.execute_turn("Interrupt me")

    def test_cli_main_argparse(self, mock_runtime):
        with patch("core.cli.get_runtime", return_value=mock_runtime):
            with patch("sys.argv", ["cli.py", "--status"]):
                assert cli_main() == 0

            with patch("sys.argv", ["cli.py", "-m", "coder", "Hello agent"]):
                assert cli_main() == 0
