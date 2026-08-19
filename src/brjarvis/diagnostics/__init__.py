# src/brjarvis/diagnostics/__init__.py
from __future__ import annotations

from brjarvis.diagnostics.doctor import (
    DoctorReport,
    auto_install_package,
    check_module,
    run_diagnostics_audit,
)

__all__ = [
    "run_diagnostics_audit",
    "check_module",
    "auto_install_package",
    "DoctorReport",
]
