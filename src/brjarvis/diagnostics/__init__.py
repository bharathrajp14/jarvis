# src/brjarvis/diagnostics/__init__.py
from __future__ import annotations

from brjarvis.diagnostics.doctor import (
    run_diagnostics_audit,
    check_module,
    auto_install_package,
    DoctorReport,
)

__all__ = [
    "run_diagnostics_audit",
    "check_module",
    "auto_install_package",
    "DoctorReport",
]
