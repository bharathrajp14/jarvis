# redteam/vuln_scanner.py — Subprocess Wrapper for Authorized Vulnerability Scanners
from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redteam.scope import ScopeEnforcer


class VulnScanner:
    """Wrapper for external security scanners (nmap, nuclei) with scope enforcement."""

    def __init__(self, scope: "ScopeEnforcer"):
        self.scope = scope

    def _check(self, target: str):
        if not self.scope.is_authorized(target):
            raise PermissionError(f"Target '{target}' is OUT OF SCOPE!")

    def nmap_service_scan(self, host: str) -> str:
        """Run service & OS detection via nmap if installed."""
        self._check(host)
        if not shutil.which("nmap"):
            return "WARNING: 'nmap' binary is not installed on this system."

        result = subprocess.run(
            ["nmap", "-sV", "-O", "--open", host],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120
        )
        self.scope.audit_log("nmap_service_scan", host, "ok")
        return result.stdout

    def nuclei_scan(self, target: str, templates: str = "cves/") -> str:
        """Run vulnerability template scan via nuclei if installed."""
        self._check(target)
        if not shutil.which("nuclei"):
            return "WARNING: 'nuclei' binary is not installed on this system."

        result = subprocess.run(
            ["nuclei", "-u", target, "-t", templates, "-silent"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300
        )
        self.scope.audit_log("nuclei_scan", target, "ok")
        return result.stdout
