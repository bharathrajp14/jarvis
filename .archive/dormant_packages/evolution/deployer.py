# evolution/deployer.py — Automated Patch Deployer
"""
Applies validated LOW and MEDIUM risk patches, creating pre-deploy snapshots
and invoking Guardian Rollback on healthcheck failures.
"""
from __future__ import annotations

from pathlib import Path
from guardian.core import GuardianCore
from guardian.snapshot import SnapshotManager
from guardian.rollback import RollbackEngine
from guardian.audit_log import AuditLog
from evolution.classifier import ChangeClassifier, RiskLevel
from evolution.sandbox import SandboxRunner
from evolution.digest import ChangeDigest


class AutoDeployer:
    """Deploys candidate patches safely with pre-deploy snapshots and rollbacks."""

    def __init__(self, guardian: GuardianCore | None = None):
        self.guardian = guardian or GuardianCore()

    def process_and_deploy(self, proposal: dict) -> dict:
        """Process a proposal: classify, test in sandbox, snapshot, deploy, and verify."""
        target_files = proposal.get("target_files", [])
        risk = ChangeClassifier.classify_patch(target_files)
        proposal["risk_level"] = risk.value

        # 1. High Risk patches route to Digest for human approval
        if risk == RiskLevel.HIGH and proposal.get("status") != "APPROVED":
            ChangeDigest.queue_proposal(proposal)
            AuditLog.log(
                event_type="PATCH_QUEUED_DIGEST",
                title=proposal.get("title", "High-Risk Proposal"),
                details=proposal,
                risk_level="HIGH",
                applied=False,
            )
            return {"deployed": False, "reason": "Queued to Change Digest for approval", "risk": risk.value}

        # 2. Run Sandbox verification tests
        sandbox_res = SandboxRunner.test_patch(proposal.get("files", {}))
        if not sandbox_res["success"]:
            AuditLog.log(
                event_type="PATCH_SANDBOX_FAILED",
                title=proposal.get("title", "Patch Proposal"),
                details=sandbox_res,
                risk_level=risk.value,
                applied=False,
            )
            return {"deployed": False, "reason": "Sandbox tests failed", "results": sandbox_res}

        # 3. Create Pre-Deploy Snapshot
        snap_info = SnapshotManager.create_snapshot(tag_prefix=f"pre_deploy_{risk.value}")

        # 4. Apply changes (write files)
        try:
            files_map = proposal.get("files", {})
            for rel_path, content in files_map.items():
                p = Path(rel_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
        except Exception as e:
            # Revert on write exception
            RollbackEngine.rollback_to_latest()
            return {"deployed": False, "reason": f"Write exception: {e}"}

        # 5. Post-Deploy Healthcheck Verification
        post_verify = SandboxRunner.test_patch({})
        if not post_verify["success"]:
            # Automatic Rollback
            rb_res = RollbackEngine.rollback_to_latest()
            AuditLog.log(
                event_type="PATCH_ROLLBACK",
                title=proposal.get("title", "Patch Proposal"),
                details={"post_verify": post_verify, "rollback": rb_res},
                risk_level=risk.value,
                applied=False,
            )
            return {"deployed": False, "reason": "Post-deploy healthcheck failed, rolled back", "rollback": rb_res}

        # 6. Rehash Guardian integrity baseline on successful deploy
        try:
            self.guardian.rehash_integrity()
        except Exception:
            pass

        # 7. Log success
        AuditLog.log(
            event_type="PATCH_DEPLOYED",
            title=proposal.get("title", "Patch Proposal"),
            details={"snapshot": snap_info, "risk": risk.value},
            risk_level=risk.value,
            applied=True,
        )

        return {"deployed": True, "risk": risk.value, "snapshot": snap_info}
