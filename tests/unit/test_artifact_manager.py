# tests/unit/test_artifact_manager.py — Unit Tests for ArtifactManager & Safe Export
from __future__ import annotations

import concurrent.futures
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from agent.artifacts import (
    ArtifactManager,
    ArtifactRecord,
    ALLOWED_ARTIFACT_EXTENSIONS,
    BLOCKED_ARTIFACT_NAMES,
    BLOCKED_ARTIFACT_EXTENSIONS,
    get_artifact_manager,
)


class TestArtifactManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="jarvis_test_art_")
        self.sandbox_dir = Path(self.temp_dir) / "sandbox_jail"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.host_artifacts_dir = Path(self.temp_dir) / "host_artifacts"
        self.host_artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.mgr = ArtifactManager(host_artifacts_dir=self.host_artifacts_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_html_artifact_success(self):
        # 1. Create HTML file inside sandbox
        html_src = self.sandbox_dir / "report.html"
        html_content = "<html><body><h1>JARVIS Analysis Report</h1></body></html>"
        html_src.write_text(html_content, encoding="utf-8")

        # 2. Export to host
        rec = self.mgr.export_sandbox_artifact(html_src, task_id="task_123")

        # 3. Assert record semantics
        self.assertTrue(rec.created)
        self.assertTrue(rec.exported)
        self.assertTrue(rec.host_verified)
        self.assertFalse(rec.browser_verified)
        self.assertEqual(rec.filename, "report.html")
        self.assertEqual(rec.mime_type, "text/html")
        self.assertIsNotNone(rec.host_path)

        # 4. Assert host file exists & content/hash matches
        host_p = Path(rec.host_path)
        self.assertTrue(host_p.exists())
        self.assertEqual(host_p.read_text(encoding="utf-8"), html_content)
        self.assertEqual(rec.sha256, self.mgr.compute_sha256(host_p))
        self.assertEqual(rec.sha256, self.mgr.compute_sha256(html_src))

    def test_missing_source_file(self):
        missing_src = self.sandbox_dir / "ghost_file.html"
        rec = self.mgr.export_sandbox_artifact(missing_src, task_id="task_fail")

        self.assertFalse(rec.created)
        self.assertFalse(rec.exported)
        self.assertFalse(rec.host_verified)
        self.assertIn("Source artifact not found", rec.error or "")

    def test_security_blocked_extensions(self):
        # Disallow executable / script exports
        for bad_ext in [".exe", ".sh", ".bat", ".ps1", ".pem", ".key", ".env"]:
            bad_file = self.sandbox_dir / f"payload{bad_ext}"
            bad_file.write_text("malicious content", encoding="utf-8")
            rec = self.mgr.export_sandbox_artifact(bad_file)
            self.assertFalse(rec.exported, f"Expected {bad_ext} to be blocked")
            self.assertIn("Security export violation", rec.error or "")

    def test_security_blocked_filenames(self):
        # Disallow .env, SSH keys, credentials
        for bad_name in [".env", ".env.local", "id_rsa", "credentials", "secrets.json"]:
            bad_file = self.sandbox_dir / bad_name
            bad_file.write_text("secret_token=12345", encoding="utf-8")
            rec = self.mgr.export_sandbox_artifact(bad_file)
            self.assertFalse(rec.exported, f"Expected {bad_name} to be blocked")
            self.assertIn("Security export violation", rec.error or "")

    def test_path_traversal_prevention(self):
        src_file = self.sandbox_dir / "traversal.html"
        src_file.write_text("safe content", encoding="utf-8")

        # Attempt to export with path traversal filename
        rec = self.mgr.export_sandbox_artifact(src_file, custom_filename="../../evil.html")
        self.assertTrue(rec.exported)
        # Verify destination is inside host_artifacts_dir and does not escape
        host_p = Path(rec.host_path)
        self.assertEqual(host_p.parent.resolve(), self.host_artifacts_dir.resolve())
        self.assertEqual(host_p.name, "evil.html")

    def test_duplicate_filename_collision_avoidance(self):
        # Export first artifact
        src1 = self.sandbox_dir / "chart.png"
        src1.write_bytes(b"PNG_DATA_1")
        rec1 = self.mgr.export_sandbox_artifact(src1)
        self.assertTrue(rec1.exported)
        self.assertEqual(Path(rec1.host_path).name, "chart.png")

        # Export second artifact with same name but allow_overwrite=False
        src2 = self.sandbox_dir / "chart.png"
        src2.write_bytes(b"PNG_DATA_2")
        rec2 = self.mgr.export_sandbox_artifact(src2, allow_overwrite=False)
        self.assertTrue(rec2.exported)
        self.assertNotEqual(rec1.host_path, rec2.host_path)
        self.assertEqual(Path(rec2.host_path).name, "chart_1.png")

        # Verify contents did not overwrite
        self.assertEqual(Path(rec1.host_path).read_bytes(), b"PNG_DATA_1")
        self.assertEqual(Path(rec2.host_path).read_bytes(), b"PNG_DATA_2")

    def test_ensure_host_artifact_routing(self):
        # 1. Web URL passes through
        ok, target, rec = self.mgr.ensure_host_artifact("https://google.com")
        self.assertTrue(ok)
        self.assertEqual(target, "https://google.com")
        self.assertIsNone(rec)

        # 2. Raw sandbox path auto-exports
        sandbox_html = self.sandbox_dir / "jarvis_sandbox_jails" / "jail_abc" / "output.html"
        sandbox_html.parent.mkdir(parents=True, exist_ok=True)
        sandbox_html.write_text("<h1>Hello from sandbox</h1>", encoding="utf-8")

        ok, target, rec = self.mgr.ensure_host_artifact(str(sandbox_html))
        self.assertTrue(ok)
        self.assertNotIn("jarvis_sandbox_jails", target)
        self.assertTrue(Path(target).exists())
        self.assertEqual(Path(target).read_text(encoding="utf-8"), "<h1>Hello from sandbox</h1>")

    def test_concurrent_artifact_exports(self):
        def _export_worker(idx: int) -> bool:
            f = self.sandbox_dir / f"concurrent_{idx}.json"
            f.write_text(f'{{"idx": {idx}}}', encoding="utf-8")
            rec = self.mgr.export_sandbox_artifact(f)
            return rec.exported and Path(rec.host_path).exists()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_export_worker, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), 20)
        self.assertTrue(all(results))
        self.assertEqual(len(self.mgr.list_artifacts()), 20)


if __name__ == "__main__":
    unittest.main()
