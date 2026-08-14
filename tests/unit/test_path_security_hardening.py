# tests/unit/test_path_security_hardening.py — Unit Tests for Path Security and Sandboxing Boundaries
from __future__ import annotations

import unittest
from pathlib import Path
from security.path_policy import (
    PathSecurityPolicy,
    PathTier,
    get_path_policy,
)


class TestPathSecurityHardening(unittest.TestCase):

    def setUp(self):
        self.policy = PathSecurityPolicy(workspace_root=Path.cwd())

    def test_safe_workspace_path(self):
        main_file = Path.cwd() / "main.py"
        self.assertTrue(self.policy.is_safe_resource(main_file))
        self.assertEqual(self.policy.get_tier(main_file), PathTier.TIER_0_WORKSPACE)
        self.assertTrue(self.policy.allow_cloud_context(main_file))

    def test_critical_system_file_denied(self):
        sam_path = "C:/Windows/System32/config/SAM"
        self.assertFalse(self.policy.is_safe_resource(sam_path))
        self.assertEqual(self.policy.get_tier(sam_path), PathTier.TIER_2_CRITICAL_SECRETS)
        self.assertFalse(self.policy.allow_cloud_context(sam_path))

    def test_ssh_keys_denied(self):
        ssh_key = Path.home() / ".ssh" / "id_rsa"
        self.assertFalse(self.policy.is_safe_resource(ssh_key))
        self.assertEqual(self.policy.get_tier(ssh_key), PathTier.TIER_2_CRITICAL_SECRETS)
        self.assertFalse(self.policy.allow_cloud_context(ssh_key))

    def test_secret_extension_denied(self):
        secret_file = Path.cwd() / "credentials.pem"
        self.assertFalse(self.policy.is_safe_resource(secret_file))
        self.assertEqual(self.policy.get_tier(secret_file), PathTier.TIER_2_CRITICAL_SECRETS)

    def test_canonicalization_normalizes_traversal(self):
        rel_traversal = Path.cwd() / "core" / ".." / "main.py"
        canonical = self.policy.canonicalize(rel_traversal)
        self.assertEqual(canonical, (Path.cwd() / "main.py").resolve())


if __name__ == "__main__":
    unittest.main()
