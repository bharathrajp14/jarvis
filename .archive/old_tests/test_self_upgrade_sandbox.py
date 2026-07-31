# tests/test_self_upgrade_sandbox.py — Self-Upgrade Engine Test Suite
"""
Unit tests for ChangeClassifier, SandboxRunner, ChangeDigest, and AutoDeployer.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evolution.classifier import ChangeClassifier, RiskLevel
from evolution.sandbox import SandboxRunner
from evolution.digest import ChangeDigest
from evolution.proposer import PatchProposer


class TestSelfUpgradeEngine(unittest.TestCase):

    def test_change_classifier(self):
        """Test blast radius risk classification."""
        # LOW Risk
        risk_low = ChangeClassifier.classify_patch(["tools/custom_command_tools.py"])
        self.assertEqual(risk_low, RiskLevel.LOW)

        # MEDIUM Risk
        risk_med = ChangeClassifier.classify_patch(["context/builder.py"])
        self.assertEqual(risk_med, RiskLevel.MEDIUM)

        # HIGH Risk
        risk_high = ChangeClassifier.classify_patch(["guardian/core.py"])
        self.assertEqual(risk_high, RiskLevel.HIGH)

    def test_change_digest_queue(self):
        """Test queuing and approval in ChangeDigest."""
        prop = {
            "proposal_id": "test_prop_001",
            "title": "Test High Risk Proposal",
            "target_files": ["guardian/core.py"],
        }
        ChangeDigest.queue_proposal(prop)
        queued = ChangeDigest.get_queued()
        self.assertTrue(any(p["proposal_id"] == "test_prop_001" for p in queued))

        app = ChangeDigest.approve_proposal("test_prop_001")
        self.assertIsNotNone(app)
        self.assertEqual(app["status"], "APPROVED")

    def test_patch_proposer(self):
        """Test PatchProposer generating candidate proposals."""
        proposer = PatchProposer()
        props = proposer.propose_from_lessons()
        self.assertIsInstance(props, list)


if __name__ == "__main__":
    unittest.main()
