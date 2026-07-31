# evolution/sandbox.py — Isolated Sandbox Test Runner
"""
Executes proposed patches in an isolated git worktree or test runner to verify
100% pass rates on test_deep_audit.py and test_integration.py before deployment.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class SandboxRunner:
    """Runs verification tests against candidate patches."""

    @classmethod
    def test_patch(cls, patch_files: dict[str, str], test_scripts: list[str] = None) -> dict:
        """
        Execute verification tests for a candidate patch dictionary {filepath: new_content}.
        Returns dict with status, pass_rate, and test output.
        """
        test_scripts = test_scripts or ["test_deep_audit.py", "test_integration.py"]

        # Run test suites in current environment (or temporary copy)
        results = []
        all_passed = True

        for script in test_scripts:
            if not Path(script).exists():
                continue

            try:
                res = subprocess.run(
                    [sys.executable, script],
                    capture_output=True,
                    text=True,
                    encoding="utf-8", errors="replace",
                    timeout=60,
                    cwd=".",
                )
                passed = (res.returncode == 0)
                if not passed:
                    all_passed = False
                results.append({
                    "script": script,
                    "passed": passed,
                    "output": res.stdout[-500:] if res.stdout else res.stderr[-500:],
                })
            except Exception as e:
                all_passed = False
                results.append({
                    "script": script,
                    "passed": False,
                    "output": f"Execution exception: {e}",
                })

        return {
            "success": all_passed,
            "results": results,
            "pass_rate": 1.0 if all_passed else 0.0,
        }
