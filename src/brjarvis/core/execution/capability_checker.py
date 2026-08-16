# core/execution/capability_checker.py — Preflight Capability Verification Engine
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dependency_resolver import get_dependency_resolver
from .environment_resolver import get_environment_resolver
from .types import DependencyDeclaration, EnvironmentProfile, RuntimeType

logger = logging.getLogger("JARVIS.CapabilityChecker")


@dataclass
class CapabilityStatus:
    """Diagnostic status of an individual system capability."""
    capability_name: str
    is_available: bool = True
    reason: str = ""
    target_environment: Optional[EnvironmentProfile] = None
    missing_items: List[str] = field(default_factory=list)
    suggested_fix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_name": self.capability_name,
            "is_available": self.is_available,
            "reason": self.reason,
            "target_environment": self.target_environment.to_dict() if self.target_environment else None,
            "missing_items": self.missing_items,
            "suggested_fix": self.suggested_fix,
        }


class CapabilityChecker:
    """
    Preflight Capability Verification Engine.
    Validates runtime requirements BEFORE executing complex multi-step workflows.
    """

    def __init__(self, env_resolver=None, dep_resolver=None):
        self.env_resolver = env_resolver or get_environment_resolver()
        self.dep_resolver = dep_resolver or get_dependency_resolver()

    def check_python_code_execution(self, code_snippet: str, project_root: Optional[Path | str] = None) -> CapabilityStatus:
        """Preflight check for executing a Python code snippet."""
        env = self.env_resolver.resolve_python(project_root=project_root)
        imports = self.dep_resolver.extract_python_imports(code_snippet)
        
        declaration = DependencyDeclaration(
            runtime=RuntimeType.PYTHON,
            import_names=list(imports),
        )
        report = self.dep_resolver.verify_dependencies(declaration, env=env, project_root=project_root)
        
        if report.satisfied:
            return CapabilityStatus(
                capability_name="python_code_execution",
                is_available=True,
                reason="All required Python modules are installed in target runtime.",
                target_environment=env,
            )
        
        fix_cmd = f"{env.executable} -m pip install {' '.join(report.missing_packages)}"
        return CapabilityStatus(
            capability_name="python_code_execution",
            is_available=False,
            reason=f"Missing dependencies in {env.precedence_source} ({env.executable}): {report.error_summary}",
            target_environment=env,
            missing_items=report.missing_packages,
            suggested_fix=fix_cmd,
        )

    def check_document_generation(self, fmt: str = "docx", project_root: Optional[Path | str] = None) -> CapabilityStatus:
        """Preflight check for document creation (docx, pdf, xlsx, pptx)."""
        fmt = fmt.lower().strip()
        env = self.env_resolver.resolve_python(project_root=project_root)
        
        req_map = {
            "docx": (["docx"], []),
            "pdf": (["pypdf"], []),
            "xlsx": (["openpyxl"], []),
            "pptx": (["pptx"], []),
            "html": ([], []),
            "md": ([], []),
        }

        imports, pkgs = req_map.get(fmt, ([], []))
        declaration = DependencyDeclaration(
            runtime=RuntimeType.PYTHON,
            import_names=imports,
            packages=pkgs,
        )
        report = self.dep_resolver.verify_dependencies(declaration, env=env, project_root=project_root)

        if report.satisfied:
            return CapabilityStatus(
                capability_name=f"document_generation_{fmt}",
                is_available=True,
                reason=f"Document generation requirements for '{fmt}' are satisfied.",
                target_environment=env,
            )

        fix_cmd = f"{env.executable} -m pip install {' '.join(report.missing_packages)}"
        return CapabilityStatus(
            capability_name=f"document_generation_{fmt}",
            is_available=False,
            reason=f"Missing library for format '{fmt}': {report.error_summary}",
            target_environment=env,
            missing_items=report.missing_packages,
            suggested_fix=fix_cmd,
        )

    def check_browser_automation(self) -> CapabilityStatus:
        """Preflight check for browser automation (Playwright + Chromium)."""
        py_env = self.env_resolver.resolve_python()
        browser_env = self.env_resolver.resolve_browser()

        # Check playwright package
        is_installed, _ = self.dep_resolver.verify_python_import("playwright", py_env)
        if not is_installed:
            return CapabilityStatus(
                capability_name="browser_automation",
                is_available=False,
                reason="Playwright Python library is not installed.",
                target_environment=py_env,
                missing_items=["playwright"],
                suggested_fix=f"{py_env.executable} -m pip install playwright && {py_env.executable} -m playwright install chromium",
            )

        if not browser_env.is_healthy:
            return CapabilityStatus(
                capability_name="browser_automation",
                is_available=False,
                reason="Playwright Chromium browser binary is not installed.",
                target_environment=browser_env,
                missing_items=["chromium_binary"],
                suggested_fix=f"{py_env.executable} -m playwright install chromium",
            )

        return CapabilityStatus(
            capability_name="browser_automation",
            is_available=True,
            reason=f"Playwright and Chromium binary ({browser_env.executable}) verified.",
            target_environment=browser_env,
        )

    def check_git_operations(self, repo_path: Optional[Path | str] = None) -> CapabilityStatus:
        """Preflight check for Git repository operations."""
        git_env = self.env_resolver.resolve_git()
        if not git_env.is_healthy:
            return CapabilityStatus(
                capability_name="git_operations",
                is_available=False,
                reason="Git executable was not found on system PATH.",
                target_environment=git_env,
                missing_items=["git"],
                suggested_fix="Install Git from https://git-scm.com or add git to system PATH.",
            )

        rp = Path(repo_path) if repo_path else self.env_resolver.default_project_root
        git_dir = rp / ".git"
        if not git_dir.exists():
            return CapabilityStatus(
                capability_name="git_operations",
                is_available=False,
                reason=f"Path '{rp}' is not a valid Git repository (.git directory missing).",
                target_environment=git_env,
                missing_items=[".git"],
                suggested_fix=f"Run: git init '{rp}'",
            )

        return CapabilityStatus(
            capability_name="git_operations",
            is_available=True,
            reason="Git executable and repository directory verified.",
            target_environment=git_env,
        )

    def check_artifact_directory(self, target_dir: Optional[Path | str] = None) -> CapabilityStatus:
        """Preflight check verifying that target artifact directory exists and is writable."""
        root = Path(target_dir) if target_dir else (self.env_resolver.default_project_root / "workspace" / "Documents")
        try:
            root.mkdir(parents=True, exist_ok=True)
            test_file = root / f".write_test_{os.getpid()}"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            return CapabilityStatus(
                capability_name="artifact_directory",
                is_available=True,
                reason=f"Artifact directory '{root}' is accessible and writable.",
            )
        except Exception as e:
            return CapabilityStatus(
                capability_name="artifact_directory",
                is_available=False,
                reason=f"Artifact directory '{root}' is not writable: {e}",
                missing_items=[str(root)],
                suggested_fix=f"Ensure write permissions on '{root}'.",
            )


_GLOBAL_CAPABILITY_CHECKER: Optional[CapabilityChecker] = None


def get_capability_checker() -> CapabilityChecker:
    global _GLOBAL_CAPABILITY_CHECKER
    if _GLOBAL_CAPABILITY_CHECKER is None:
        _GLOBAL_CAPABILITY_CHECKER = CapabilityChecker()
    return _GLOBAL_CAPABILITY_CHECKER
