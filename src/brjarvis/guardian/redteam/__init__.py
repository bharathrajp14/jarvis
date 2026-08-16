"""BR JARVIS Red Team Security Audit Package."""
from __future__ import annotations

import sys

from . import recon, report, scope, vuln_scanner
from .scope import ScopeEnforcer, DEFAULT_SCOPE
from .recon import ReconEngine
from .report import generate_report, generate_html_report
from .vuln_scanner import VulnScanner

# Register legacy top-level aliases
_self = sys.modules[__name__]
sys.modules.setdefault("redteam", _self)
sys.modules.setdefault("brjarvis.guardian.redteam", _self)
# Register submodule aliases so "from redteam.scope import X" works
for _sub in ("scope", "recon", "report", "vuln_scanner"):
    _full = f"{__name__}.{_sub}"
    _alias = f"redteam.{_sub}"
    if _full in sys.modules:
        sys.modules.setdefault(_alias, sys.modules[_full])

__all__ = [
    "recon",
    "report",
    "scope",
    "vuln_scanner",
    "ScopeEnforcer",
    "DEFAULT_SCOPE",
    "ReconEngine",
    "generate_report",
    "generate_html_report",
    "VulnScanner",
]

