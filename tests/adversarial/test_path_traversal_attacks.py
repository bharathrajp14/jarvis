"""Adversarial Security Tests: Path Traversal & Sandbox Escape Attempts."""
from __future__ import annotations

import pytest
from brjarvis.security.path_policy import get_path_policy, PathTier


@pytest.mark.adversarial
def test_path_traversal_relative_parent_escape():
    """Verify dot-dot traversal escaping workspace is flagged as critical secret / unsafe."""
    policy = get_path_policy()
    evil_paths = [
        "../../../../Windows/System32/config/SAM",
        "workspace/../../../../etc/shadow",
        "..\\..\\..\\Windows\\win.ini",
        "workspace/..\\..\\secrets.json",
        ".env",
        ".env.local"
    ]
    for p in evil_paths:
        assert policy.is_safe_resource(p) is False or policy.get_tier(p) == PathTier.TIER_2_CRITICAL_SECRETS
