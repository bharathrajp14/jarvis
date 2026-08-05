# tests/test_guardian.py — Guardian Core & Safety Test Suite
"""
Unit tests for Guardian Core, KillSwitch, SnapshotManager, RollbackEngine, and PathPolicy.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from guardian.core import GuardianCore
from guardian.kill_switch import KillSwitch
from guardian.snapshot import SnapshotManager
from guardian.rollback import RollbackEngine
from guardian.audit_log import AuditLog
from permissions import PathPolicy, PathTier, cloud_context_exclusion_check


class TestGuardianSafety(unittest.TestCase):

    def test_kill_switch_pause_resume(self):
        """Test KillSwitch pause and resume cycles."""
        KillSwitch.resume()
        self.assertFalse(KillSwitch.is_paused())

        KillSwitch.pause(reason="Unit test pause")
        self.assertTrue(KillSwitch.is_paused())
        self.assertIn("Unit test pause", KillSwitch.get_pause_reason())

        KillSwitch.resume()
        self.assertFalse(KillSwitch.is_paused())

    def test_path_policy_tiers(self):
        """Test PathPolicy file path classification into Tiers 0, 1, and 2."""
        # Dynamic Tier 0 Workspace using absolute local paths
        workspace_root = Path(__file__).resolve().parent.parent
        workspace_file = workspace_root / "main.py"
        self.assertEqual(PathPolicy.get_tier(str(workspace_file)), PathTier.TIER_0_WORKSPACE)
        self.assertTrue(cloud_context_exclusion_check(str(workspace_file)))

        # Tier 1 User Profile (outside workspace)
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file = Path(temp_dir) / "jarvis_temp_test_file.py"
        # If temp path is outside workspace, it should fall into Tier 1
        if not str(temp_file).replace("\\", "/").lower().startswith(str(workspace_root).replace("\\", "/").lower()):
            self.assertEqual(PathPolicy.get_tier(str(temp_file)), PathTier.TIER_1_USER_PROFILE)

        # Tier 2 Critical / Secrets
        self.assertEqual(PathPolicy.get_tier("C:/Windows/System32/config/SAM"), PathTier.TIER_2_CRITICAL_SECRETS)
        self.assertEqual(PathPolicy.get_tier("C:/Users/user/.ssh/id_rsa"), PathTier.TIER_2_CRITICAL_SECRETS)
        self.assertEqual(PathPolicy.get_tier("d:/secret/key.pem"), PathTier.TIER_2_CRITICAL_SECRETS)
        self.assertFalse(cloud_context_exclusion_check("C:/Users/user/.ssh/id_rsa"))

    def test_snapshot_creation(self):
        """Test SnapshotManager snapshot creation."""
        snap = SnapshotManager.create_snapshot(tag_prefix="test_snap")
        self.assertIsNotNone(snap)
        self.assertIn("snapshot_id", snap)
        self.assertTrue(Path(snap["path"]).exists())

    def test_guardian_integrity(self):
        """Test GuardianCore integrity verification."""
        guardian = GuardianCore()
        check = guardian.verify_integrity()
        self.assertTrue(check["valid"])


if __name__ == "__main__":
    unittest.main()
