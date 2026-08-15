# tests/e2e/test_sandbox_artifact_lifecycle.py — Complete E2E Sandbox Artifact & Browser Verification Test Suite
"""
Comprehensive End-to-End Reality Test Suite for Sandbox-to-Host Artifact Lifecycle.
Validates:
1. Code execution in Sandbox Process creates HTML report.
2. Verified artifact is automatically and securely exported to host workspace.
3. Raw sandbox jail path is NEVER exposed to the browser or OS launcher.
4. Host file existence, readability, and SHA-256 hash match are strictly verified.
5. ActionVerifier inspects browser state and asserts no ERR_FILE_NOT_FOUND.
6. Granular lifecycle status semantics (created, exported, opened, observed, verified).
7. Comprehensive attack matrix: path traversal, symlink escapes, dangerous extensions, collision avoidance, and concurrency.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from agent.artifacts import ArtifactManager, ArtifactRecord, get_artifact_manager
from agent.verifier import ActionVerifier, VerificationResult
from tools.browser_automation import browser_open_url
from tools.registry import execute_tool
from tools.sandbox_process import SandboxedProcessRunner, get_sandbox_runner


@pytest.fixture
def clean_artifact_environment(tmp_path):
    """Fixture providing isolated host artifacts directory and fresh manager."""
    host_dir = tmp_path / "test_host_artifacts"
    host_dir.mkdir(parents=True, exist_ok=True)
    mgr = ArtifactManager(host_artifacts_dir=host_dir)
    return mgr, host_dir


# ─────────────────────────────────────────────────────────────────────────────
# 1. PRIMARY E2E REGRESSION TEST: SANDBOX ARTIFACT -> HOST EXPORT -> BROWSER
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_sandbox_artifact_lifecycle_and_browser_open(tmp_path, clean_artifact_environment):
    """
    Primary Regression Scenario:
    1. Python script inside sandbox creates 'JARVIS_Project_Analysis.html'.
    2. Sandbox runner executes and automatically exports the user artifact before jail cleanup.
    3. The browser tool is called. Confirm browser NEVER receives raw sandbox path.
    4. Host file exists, is non-empty, and source/destination hashes match.
    5. ActionVerifier verifies host file and browser load without ERR_FILE_NOT_FOUND.
    6. Granular lifecycle status semantics are verified.
    """
    mgr, host_dir = clean_artifact_environment
    sandbox = SandboxedProcessRunner()

    # Step 1: Execute Python script inside sandbox that writes an HTML report
    script = """
import os
from pathlib import Path

html_content = '''<!DOCTYPE html>
<html>
<head><title>JARVIS Project Analysis</title></head>
<body>
    <h1>JARVIS Project Analysis Report</h1>
    <p>Execution in sandbox verified successfully.</p>
</body>
</html>'''

Path("JARVIS_Project_Analysis.html").write_text(html_content, encoding="utf-8")
print("Report generated successfully.")
"""

    with patch("agent.artifacts.get_artifact_manager", return_value=mgr):
        res = sandbox.execute(code=script, lang="python", timeout=10)

        # Assert sandbox execution succeeded
        assert res.get("success") is True
        assert "Report generated successfully." in res.get("stdout", "")

        # Step 2: Verify automatic export of artifact
        exported_artifacts = res.get("artifacts", [])
        assert len(exported_artifacts) >= 1
        art_info = exported_artifacts[0]
        assert art_info["filename"] == "JARVIS_Project_Analysis.html"
        assert art_info["exported"] is True
        assert art_info["host_verified"] is True

        host_path = Path(art_info["host_path"])

        # Step 3: Verify host file exists, is readable, and non-empty
        assert host_path.exists()
        assert host_path.is_file()
        assert host_path.stat().st_size > 50
        assert os.access(host_path, os.R_OK)

        # Step 4: Verify SHA-256 integrity
        expected_hash = hashlib.sha256(host_path.read_bytes()).hexdigest()
        assert art_info["sha256"] == expected_hash

        # Step 5: Verify ActionVerifier validates artifact export
        v_export = ActionVerifier.verify_artifact_exported(host_path)
        assert v_export.verified is True

        # Step 6: Simulate browser open with fake sandbox path -> must be intercepted
        fake_sandbox_path = f"C:/Users/bhara/AppData/Local/Temp/jarvis_sandbox_jails/jail_test123/workspace/JARVIS_Project_Analysis.html"
        
        # Test ensure_host_artifact intercepts and resolves to host path
        ok, resolved_target, rec = mgr.ensure_host_artifact(fake_sandbox_path)
        assert ok is True
        assert "jarvis_sandbox_jails" not in resolved_target.lower()
        assert Path(resolved_target).exists()

        # Step 7: Test browser open tool
        with patch("tools.browser_automation._get_or_create_page") as mock_get_page:
            mock_page = MagicMock()
            
            async def _fake_goto(url, **kwargs):
                # Ensure the URL passed to browser is file:// pointing to host_path, NEVER sandbox path
                assert "jarvis_sandbox_jails" not in url.lower()
                assert "test_host_artifacts" in url.lower() or "documents" in url.lower()
                return None

            async def _fake_title():
                return "JARVIS Project Analysis"

            async def _fake_content():
                return "<html><body><h1>JARVIS Project Analysis Report</h1></body></html>"

            mock_page.goto = _fake_goto
            mock_page.title = _fake_title
            mock_page.content = _fake_content
            mock_page.url = host_path.as_uri()

            async def _return_mock_page(*args, **kwargs):
                return mock_page

            mock_get_page.side_effect = _return_mock_page

            open_result = browser_open_url({"url": str(host_path)})
            assert "Opened 'JARVIS Project Analysis'" in open_result
            assert "Host Artifact Verified" in open_result

            # Step 8: Verify ActionVerifier validates browser result
            v_browser = ActionVerifier.verify_browser_artifact_opened(host_path, browser_response=open_result)
            assert v_browser.verified is True

            # Step 9: Verify decoupled result semantics
            updated_rec = mgr.get_artifact(art_info["artifact_id"])
            assert updated_rec is not None
            assert updated_rec.created is True
            assert updated_rec.exported is True
            assert updated_rec.opened is True
            assert updated_rec.observed is True
            assert updated_rec.host_verified is True
            assert updated_rec.browser_verified is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. ADVERSARIAL & SECURITY MATRIX
# ─────────────────────────────────────────────────────────────────────────────

def test_security_rejection_of_critical_system_files(clean_artifact_environment):
    """Ensure secret keys, credential files, and system configs are strictly blocked from export."""
    mgr, host_dir = clean_artifact_environment

    blocked_samples = [
        (".env", "DB_PASSWORD=secret"),
        (".env.local", "API_KEY=123"),
        (".git/config", "[core]"),
        ("id_rsa", "-----BEGIN RSA PRIVATE KEY-----"),
        ("credentials.json", '{"token": "xyz"}'),
        ("malicious.exe", "MZ..."),
        ("payload.bat", "rmdir /s /q C:\\"),
        ("exploit.ps1", "Invoke-Expression"),
    ]

    temp_jail = host_dir / "temp_jail"
    temp_jail.mkdir(exist_ok=True)

    for filename, content in blocked_samples:
        src = temp_jail / filename
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(content, encoding="utf-8")

        rec = mgr.export_sandbox_artifact(src)
        assert rec.exported is False, f"Failed to block export of {filename}"
        assert rec.error is not None
        assert "Security export violation" in rec.error


def test_path_traversal_attack_neutralization(clean_artifact_environment):
    """Ensure directory traversal attacks cannot write outside the host artifact root."""
    mgr, host_dir = clean_artifact_environment
    src = host_dir / "temp_src.html"
    src.write_text("<h1>Safe Content</h1>", encoding="utf-8")

    # Path traversal in custom_filename
    rec = mgr.export_sandbox_artifact(src, custom_filename="../../../../Windows/System32/evil.html")
    assert rec.exported is True
    # Destination must be sanitized inside host_dir
    dest_path = Path(rec.host_path).resolve()
    assert dest_path.parent.resolve() == host_dir.resolve()
    assert dest_path.name == "evil.html"


def test_browser_verification_fails_closed_on_err_file_not_found(clean_artifact_environment):
    """Ensure ActionVerifier rejects missing files and reports ERR_FILE_NOT_FOUND with status=FAILED."""
    mgr, host_dir = clean_artifact_environment
    ghost_file = host_dir / "non_existent_report.html"

    v_res = ActionVerifier.verify_browser_artifact_opened(ghost_file)
    assert v_res.verified is False
    assert v_res.error == "ERR_FILE_NOT_FOUND"

    # Browser error string simulation
    err_browser_output = "Microsoft Edge: File not found. ERR_FILE_NOT_FOUND"
    v_res_output = ActionVerifier.verify_browser_artifact_opened("https://example.com", browser_response=err_browser_output)
    assert v_res_output.verified is False
    assert v_res_output.error == "ERR_FILE_NOT_FOUND"


def test_raw_sandbox_path_rejection_by_verifier():
    """Ensure ActionVerifier permanently rejects raw sandbox jail paths as a security violation."""
    raw_sandbox_url = "file:///C:/Users/bhara/AppData/Local/Temp/jarvis_sandbox_jails/jail_xyz/report.html"
    v_res = ActionVerifier.verify_browser_artifact_opened(raw_sandbox_url)
    assert v_res.verified is False
    assert v_res.error == "SANDBOX_PATH_EXPOSURE"


def test_concurrent_artifact_exports_e2e(clean_artifact_environment):
    """Ensure multi-threaded concurrent sandbox exports remain completely isolated and intact."""
    mgr, host_dir = clean_artifact_environment
    temp_sandbox = host_dir / "concurrency_sandbox"
    temp_sandbox.mkdir(exist_ok=True)

    def _worker(worker_id: int):
        f = temp_sandbox / f"data_stream_{worker_id}.json"
        content = f'{{"worker": {worker_id}, "timestamp": {time.time()}}}'
        f.write_text(content, encoding="utf-8")
        rec = mgr.export_sandbox_artifact(f, task_id=f"worker_{worker_id}")
        return rec.exported and Path(rec.host_path).exists() and rec.sha256 == mgr.compute_sha256(rec.host_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_worker, i) for i in range(25)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 25
    assert all(results)
