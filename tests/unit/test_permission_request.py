# tests/unit/test_permission_request.py — Unit Tests for Permission Request Engine
from __future__ import annotations

from brjarvis.security.permission_request import (
    PermissionDecision,
    PermissionManager,
    PermissionRequest,
    RiskLevel,
)


class TestPermissionRequestEngine:
    """Test suite for PermissionRequest and PermissionManager."""

    def test_risk_classification(self):
        mgr = PermissionManager()
        assert mgr.classify_risk("file_read", {"path": "test.txt"}) == RiskLevel.SAFE
        assert mgr.classify_risk("web_search", {"query": "python"}) == RiskLevel.LOW
        assert mgr.classify_risk("browser_click", {"selector": "#btn"}) == RiskLevel.MEDIUM
        assert mgr.classify_risk("file_write", {"path": "main.py"}) == RiskLevel.HIGH
        assert mgr.classify_risk("file_delete", {"path": "main.py"}) == RiskLevel.CRITICAL

    def test_create_permission_request(self):
        mgr = PermissionManager()
        req = mgr.create_request(
            tool="file_delete",
            args={"path": "d:/test/data.json"},
            session_id="sess-perm-1",
            task_id="task-100",
        )
        assert req.tool == "file_delete"
        assert req.risk_level == RiskLevel.CRITICAL
        assert "data.json" in req.target
        assert "Permanent modification or deletion" in req.consequence
        assert req.status == "pending"

    def test_resolve_permission_request(self):
        req = PermissionRequest(tool="file_write", target="app.py")
        req.resolve(PermissionDecision.ALLOW_ONCE)
        assert req.status == "granted"
        assert req.decision == PermissionDecision.ALLOW_ONCE

        req2 = PermissionRequest(tool="file_delete", target="db.sqlite")
        req2.resolve(PermissionDecision.DENY)
        assert req2.status == "denied"

        req3 = PermissionRequest(tool="run_code")
        req3.resolve(PermissionDecision.CANCEL)
        assert req3.status == "cancelled"

    def test_session_scoped_pre_approvals(self):
        mgr = PermissionManager()
        sess_id = "sess-scope-test"

        # Not pre-approved initially
        assert not mgr.is_pre_approved(sess_id, "file_write", "main.py")

        # Allow tool for session
        req = mgr.create_request("file_write", {"path": "main.py"}, session_id=sess_id)
        mgr.record_decision(sess_id, req, PermissionDecision.ALLOW_TOOL)

        assert mgr.is_pre_approved(sess_id, "file_write", "main.py")
        assert mgr.is_pre_approved(sess_id, "file_write", "other.py")
        # Other dangerous tools are not pre-approved
        assert not mgr.is_pre_approved(sess_id, "file_delete", "main.py")

    def test_allow_session_scope(self):
        mgr = PermissionManager()
        sess_id = "sess-allow-all-test"

        req = mgr.create_request("run_code", {"code": "print(1)"}, session_id=sess_id)
        mgr.record_decision(sess_id, req, PermissionDecision.ALLOW_SESSION)

        assert mgr.is_pre_approved(sess_id, "run_code")
        assert mgr.is_pre_approved(sess_id, "file_delete")
        assert mgr.is_pre_approved(sess_id, "file_write")
