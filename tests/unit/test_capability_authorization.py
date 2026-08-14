# tests/unit/test_capability_authorization.py — Unit Tests for Capability-Based Security
from __future__ import annotations

import unittest
from security.capabilities import Capability, RiskLevel, ToolContract
from security.policy_engine import (
    ActionDecision,
    PermissionMode,
    PolicyContext,
    PolicyEngine,
    get_policy_engine,
)
from permissions import check_permission, evaluate_action_policy, PermissionPolicy


class TestCapabilityAuthorization(unittest.TestCase):

    def setUp(self):
        self.engine = PolicyEngine(mode=PermissionMode.CONFIRM_DESTRUCTIVE)

    def test_safe_read_only_tool_allowed(self):
        ctx = PolicyContext(
            action="file_read",
            capabilities={Capability.READ_ONLY},
            risk=RiskLevel.LOW
        )
        decision = self.engine.evaluate(ctx)
        self.assertEqual(decision, ActionDecision.ALLOW)

    def test_destructive_tool_requires_confirmation(self):
        ctx = PolicyContext(
            action="file_delete",
            capabilities={Capability.DESTRUCTIVE, Capability.FILE_MUTATION},
            risk=RiskLevel.HIGH
        )
        decision = self.engine.evaluate(ctx)
        self.assertEqual(decision, ActionDecision.CONFIRM)

    def test_critical_risk_always_requires_confirmation(self):
        ctx = PolicyContext(
            action="custom_command",
            capabilities={Capability.SYSTEM_CONTROL},
            risk=RiskLevel.CRITICAL
        )
        decision = self.engine.evaluate(ctx)
        self.assertEqual(decision, ActionDecision.CONFIRM)

    def test_session_grant_allows_action(self):
        session_id = "test_session_123"
        self.engine.grant_session_action("file_write", session_id=session_id)
        ctx = PolicyContext(
            session_id=session_id,
            action="file_write",
            capabilities={Capability.FILE_MUTATION},
            risk=RiskLevel.HIGH
        )
        decision = self.engine.evaluate(ctx)
        self.assertEqual(decision, ActionDecision.ALLOW_FOR_SESSION)

    def test_critical_resource_denylist_denies(self):
        ctx = PolicyContext(
            action="file_read",
            resource="C:/Windows/System32/config/SAM",
            capabilities={Capability.READ_ONLY},
            risk=RiskLevel.LOW
        )
        decision = self.engine.evaluate(ctx)
        self.assertEqual(decision, ActionDecision.DENY)

    def test_deny_all_mode_blocks_unauthorized_tools(self):
        engine = PolicyEngine(
            mode=PermissionMode.DENY_ALL,
            allow_names=frozenset({"help", "status"})
        )
        ctx1 = PolicyContext(action="help")
        self.assertEqual(engine.evaluate(ctx1), ActionDecision.ALLOW)

        ctx2 = PolicyContext(action="web_search")
        self.assertEqual(engine.evaluate(ctx2), ActionDecision.DENY)

    def test_fail_closed_on_invalid_data(self):
        # Even with None action, policy engine returns DENY
        decision = self.engine.evaluate(None)  # type: ignore[arg-type]
        self.assertEqual(decision, ActionDecision.DENY)


if __name__ == "__main__":
    unittest.main()
