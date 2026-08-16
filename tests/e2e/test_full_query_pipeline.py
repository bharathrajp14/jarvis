"""E2E Test: Full Natural Language Query Execution Pipeline."""
from __future__ import annotations

import pytest
from brjarvis.core.cli import run_query


@pytest.mark.e2e
def test_full_query_execution():
    """Verify executing a system query completes with 0 exit code."""
    res = run_query("status")
    assert res == 0
