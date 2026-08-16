import os
import unittest
from brjarvis.security.permissions import (
    PermissionMode,
    PermissionPolicy,
    _normalize_mode,
    evaluate_action_policy,
    ActionDecision,
    RiskLevel,
    PERMISSIONS,
)
from brjarvis.security.policy_engine import PolicyEngine, get_policy_engine


class TestSecurityPolicyPermissions(unittest.TestCase):
    def setUp(self):
        self._orig_mode = os.environ.get("JARVIS_PERMISSION_MODE")

    def tearDown(self):
        if self._orig_mode is not None:
            os.environ["JARVIS_PERMISSION_MODE"] = self._orig_mode
        else:
            os.environ.pop("JARVIS_PERMISSION_MODE", None)

    def test_normalize_mode_aliases(self):
        self.assertEqual(_normalize_mode("auto"), PermissionMode.ALLOW_ALL)
        self.assertEqual(_normalize_mode("allow_all"), PermissionMode.ALLOW_ALL)
        self.assertEqual(_normalize_mode("confirm_destructive"), PermissionMode.CONFIRM_DESTRUCTIVE)
        self.assertEqual(_normalize_mode("confirm_all"), PermissionMode.CONFIRM_ALL)
        self.assertEqual(_normalize_mode("deny"), PermissionMode.DENY_ALL)
        self.assertEqual(_normalize_mode("deny_all"), PermissionMode.DENY_ALL)

    def test_normalize_mode_env_fallback(self):
        os.environ["JARVIS_PERMISSION_MODE"] = "allow_all"
        self.assertEqual(_normalize_mode(None), PermissionMode.ALLOW_ALL)

        os.environ["JARVIS_PERMISSION_MODE"] = "confirm_all"
        self.assertEqual(_normalize_mode(None), PermissionMode.CONFIRM_ALL)

    def test_policy_engine_allow_all_mode(self):
        engine = PolicyEngine(mode="allow_all")
        self.assertEqual(engine.mode, PermissionMode.ALLOW_ALL)
        # In allow_all mode, tool permission check for destructive tools should return True (allowed)
        self.assertTrue(engine.check_tool_permission("run_code", {"code": "print('hello')"}))

    def test_policy_engine_confirm_destructive_mode(self):
        engine = PolicyEngine(mode="confirm_destructive")
        self.assertEqual(engine.mode, PermissionMode.CONFIRM_DESTRUCTIVE)
        # In confirm_destructive mode, safe reads are allowed, destructive tools are blocked/require confirmation
        self.assertTrue(engine.check_tool_permission("file_read", {"path": "test.txt"}))
        self.assertFalse(engine.check_tool_permission("file_delete", {"path": "test.txt"}))

    def test_permissions_set_mode_sync(self):
        policy = PermissionPolicy(mode="confirm_destructive")
        policy.set_mode("auto")
        self.assertEqual(policy.mode, PermissionMode.ALLOW_ALL)
        self.assertEqual(os.environ.get("JARVIS_PERMISSION_MODE"), "ALLOW_ALL")


if __name__ == "__main__":
    unittest.main()
