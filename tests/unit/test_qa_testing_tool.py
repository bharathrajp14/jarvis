# tests/test_qa_testing_tool.py — Tests for Autonomous QA Testing Suite
import json
import pytest
from tools.qa_testing_tool import (
    qa_run_browser_test,
    qa_assert_page_state,
    qa_generate_report,
)


def test_qa_tool_handlers_importable():
    """Verify tool functions are importable and callable."""
    assert callable(qa_run_browser_test)
    assert callable(qa_assert_page_state)
    assert callable(qa_generate_report)


def test_qa_generate_report_output():
    """Verify Markdown QA audit report generation."""
    sample_results = {
        "url": "http://localhost:3000",
        "passed": True,
        "step_results": [
            {"step": 1, "action": "navigate", "status": "PASS", "duration_ms": 120.5}
        ],
        "console_logs": [],
        "page_errors": []
    }
    
    report_res = qa_generate_report({
        "test_name": "Local App Test Suite",
        "results_json": json.dumps(sample_results),
        "report_filename": "test_qa_sample_report.md"
    })
    
    assert "✅ QA Audit Report generated" in report_res or "qa_sample_report.md" in report_res
