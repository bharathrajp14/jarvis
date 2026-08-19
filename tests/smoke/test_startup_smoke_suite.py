"""Non-Destructive Startup Smoke Invariant Suite for BR JARVIS MK40.2+."""

from __future__ import annotations

import pytest

from scripts.smoke_startup import main as run_smoke_checks


@pytest.mark.smoke
def test_all_startup_smoke_invariants():
    """Verify all 12 non-destructive startup invariant checks pass with 0 exit code."""
    result = run_smoke_checks()
    assert result == 0
