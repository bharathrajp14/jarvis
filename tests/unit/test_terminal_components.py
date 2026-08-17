# tests/unit/test_terminal_components.py — Unit Tests for Terminal UI Components
from __future__ import annotations

import pytest
from rich.console import Console
from io import StringIO

from brjarvis.core.terminal.components import (
    HeaderComponent,
    ToolCallComponent,
    CollapsibleOutputComponent,
    PermissionPromptComponent,
    PlanViewComponent,
    StatusPanelComponent,
)
from brjarvis.security.permission_request import PermissionRequest, RiskLevel


class TestTerminalComponents:
    """Test suite for modular terminal UI components."""

    def test_header_component_rendering(self):
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        HeaderComponent.render(
            console=console,
            session_id="sess-test-12345",
            mode="coder",
            model="Claude 3.7",
            permission_mode="confirm_destructive",
            working_dir="D:/workspace",
        )
        rendered = output.getvalue()
        assert "BR JARVIS" in rendered
        assert "CODER" in rendered
        assert "Claude 3.7" in rendered

    def test_tool_call_component(self):
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        ToolCallComponent.render_started(console, "web_search", "query='python async'")
        ToolCallComponent.render_completed(console, "web_search", duration_ms=120.0, evidence="10 results found", verified=True)
        ToolCallComponent.render_failed(console, "file_read", error_msg="File not found", duration_ms=15.0)

        rendered = output.getvalue()
        assert "web_search" in rendered
        assert "file_read" in rendered
        assert "120ms" in rendered
        assert "File not found" in rendered

    def test_collapsible_output(self):
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        # Short content - not collapsed
        CollapsibleOutputComponent.render(console, "Short Log", "Line 1\nLine 2\nLine 3", max_lines=5)
        short_rendered = output.getvalue()
        assert "hidden" not in short_rendered

        # Long content - collapsed
        output_long = StringIO()
        console_long = Console(file=output_long, force_terminal=True, width=100)
        long_content = "\n".join(f"Log line {i}" for i in range(25))
        CollapsibleOutputComponent.render(console_long, "Build Output", long_content, max_lines=6)
        long_rendered = output_long.getvalue()
        assert "lines hidden" in long_rendered

    def test_permission_prompt_component(self):
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        req = PermissionRequest(
            tool="file_delete",
            action="file_delete",
            target="d:/prod/config.yaml",
            arguments_summary="path='d:/prod/config.yaml'",
            risk_level=RiskLevel.CRITICAL,
            consequence="Permanent deletion of production config file.",
        )
        PermissionPromptComponent.render(console, req)
        rendered = output.getvalue()
        assert "file_delete" in rendered
        assert "CRITICAL" in rendered
        assert "config.yaml" in rendered

    def test_plan_view_component(self):
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        plan = {
            "goal": "Migrate Terminal Interaction Architecture",
            "steps": [
                {"step": 1, "description": "Implement AgentSession", "tool": "file_write", "status": "completed"},
                {"step": 2, "description": "Implement AgentLoop", "tool": "file_write", "status": "running"},
                {"step": 3, "description": "Run Verification Tests", "tool": "run_code", "status": "pending"},
            ],
        }
        PlanViewComponent.render(console, plan)
        rendered = output.getvalue()
        assert "Migrate Terminal" in rendered
        assert "AgentSession" in rendered
        assert "Done" in rendered
        assert "Running" in rendered
