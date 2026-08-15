# core/execution/dependency_resolver.py — Universal Dependency & Import Intelligence Engine
from __future__ import annotations

import ast
import importlib.metadata
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.execution.environment_resolver import get_environment_resolver
from core.execution.types import DependencyDeclaration, EnvironmentProfile, RuntimeType

logger = logging.getLogger("JARVIS.DependencyResolver")

# Canonical fallback mapping from Python top-level import module names to PyPI distribution names
_KNOWN_MODULE_TO_DIST: Dict[str, str] = {
    "fitz": "PyMuPDF",
    "docx": "python-docx",
    "cv2": "opencv-python",
    "PIL": "pillow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "psutil": "psutil",
    "pypdf": "pypdf",
    "openpyxl": "openpyxl",
    "pptx": "python-pptx",
    "playwright": "playwright",
    "jwt": "PyJWT",
    "fpdf": "fpdf2",
    "send2trash": "Send2Trash",
    "win32api": "pywin32",
    "win32con": "pywin32",
    "win32gui": "pywin32",
    "pywinauto": "pywinauto",
    "pycaw": "pycaw",
    "speech_recognition": "SpeechRecognition",
    "comtypes": "comtypes",
    "mss": "mss",
    "pyautogui": "PyAutoGUI",
    "pyperclip": "pyperclip",
    "pydantic": "pydantic",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "duckduckgo_search": "duckduckgo_search",
    "chromadb": "chromadb",
    "google.genai": "google-genai",
    "anthropic": "anthropic",
    "openai": "openai",
    "rich": "rich",
}


@dataclass
class DependencyCheckReport:
    """Detailed diagnostic report of dependencies checked in a specific environment."""
    satisfied: bool = True
    missing_packages: List[str] = field(default_factory=list)          # Distribution names to install
    missing_modules: List[str] = field(default_factory=list)           # Import module names that failed
    missing_executables: List[str] = field(default_factory=list)
    missing_browser_binaries: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    missing_directories: List[str] = field(default_factory=list)
    missing_credentials: List[str] = field(default_factory=list)
    installed_versions: Dict[str, str] = field(default_factory=dict)
    environment: Optional[EnvironmentProfile] = None
    error_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satisfied": self.satisfied,
            "missing_packages": self.missing_packages,
            "missing_modules": self.missing_modules,
            "missing_executables": self.missing_executables,
            "missing_browser_binaries": self.missing_browser_binaries,
            "missing_files": self.missing_files,
            "missing_directories": self.missing_directories,
            "missing_credentials": self.missing_credentials,
            "installed_versions": self.installed_versions,
            "environment": self.environment.to_dict() if self.environment else None,
            "error_summary": self.error_summary,
        }


class DependencyResolver:
    """
    Universal machine-readable dependency engine and import intelligence.
    Verifies and resolves requirements against actual target runtimes.
    """

    def __init__(self, env_resolver=None):
        self.env_resolver = env_resolver or get_environment_resolver()
        self._pkg_dist_map: Dict[str, str] = dict(_KNOWN_MODULE_TO_DIST)
        self._init_dynamic_package_map()

    def _init_dynamic_package_map(self) -> None:
        """Dynamically query Python metadata for installed module -> distribution mappings."""
        try:
            if hasattr(importlib.metadata, "packages_distributions"):
                dist_map = importlib.metadata.packages_distributions()
                for mod_name, pkgs in dist_map.items():
                    if pkgs:
                        self._pkg_dist_map[mod_name] = pkgs[0]
        except Exception as e:
            logger.debug("packages_distributions dynamic init note: %s", e)

    def map_module_to_package(self, module_name: str) -> str:
        """Map a Python import name (e.g. 'fitz', 'docx') to its PyPI package name (e.g. 'PyMuPDF', 'python-docx')."""
        clean = module_name.split(".")[0].strip()
        if clean in self._pkg_dist_map:
            return self._pkg_dist_map[clean]
        # Return module name as fallback package name
        return clean

    def extract_python_imports(self, code_snippet: str) -> Set[str]:
        """Parse Python source code AST to extract all top-level imported module names."""
        imports: Set[str] = set()
        try:
            tree = ast.parse(code_snippet)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        imports.add(top)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        imports.add(top)
        except Exception:
            # Fallback regex parsing if syntax has partial snippet or invalid grammar
            for match in re.finditer(r'^\s*(?:from|import)\s+([a-zA-Z0-9_]+)', code_snippet, re.MULTILINE):
                imports.add(match.group(1))
        
        # Filter standard library modules that never require PyPI installation
        stdlib_modules = sys.stdlib_module_names if hasattr(sys, "stdlib_module_names") else {
            "os", "sys", "re", "json", "time", "math", "random", "typing", "datetime", "pathlib",
            "subprocess", "collections", "itertools", "functools", "logging", "threading", "asyncio",
            "shutil", "tempfile", "uuid", "hashlib", "urllib", "sqlite3", "io", "copy", "traceback",
            "platform", "ctypes", "zipfile", "tarfile", "csv", "xml", "html", "unittest", "inspect"
        }
        return {m for m in imports if m not in stdlib_modules}

    def verify_dependencies(
        self,
        declaration: DependencyDeclaration,
        env: Optional[EnvironmentProfile] = None,
        project_root: Optional[Path | str] = None,
    ) -> DependencyCheckReport:
        """Check whether all requirements in declaration are satisfied in target environment."""
        target_env = env or self.env_resolver.resolve_python(project_root=project_root)
        report = DependencyCheckReport(satisfied=True, environment=target_env)

        # 1. Check Python Packages / Imports
        for imp in declaration.import_names:
            is_installed, ver = self.verify_python_import(imp, target_env)
            if is_installed:
                report.installed_versions[imp] = ver
            else:
                report.satisfied = False
                report.missing_modules.append(imp)
                pkg_name = self.map_module_to_package(imp)
                if pkg_name not in report.missing_packages:
                    report.missing_packages.append(pkg_name)

        # Reverse map for checking package distributions
        dist_to_mod = {v.lower(): k for k, v in self._pkg_dist_map.items()}
        for pkg in declaration.packages:
            mod_to_check = dist_to_mod.get(pkg.lower(), pkg)
            is_installed, ver = self.verify_python_import(mod_to_check, target_env)
            if is_installed:
                report.installed_versions[pkg] = ver
            else:
                if pkg not in report.missing_packages:
                    report.satisfied = False
                    report.missing_packages.append(pkg)

        # 2. Check Executables
        for exe in declaration.executables:
            resolved_exe = shutil.which(exe)
            if not resolved_exe:
                report.satisfied = False
                report.missing_executables.append(exe)

        # 3. Check Browser Binaries
        for b in declaration.browser_binaries:
            browser_prof = self.env_resolver.resolve_browser()
            if not browser_prof.is_healthy:
                report.satisfied = False
                report.missing_browser_binaries.append(b)

        # 4. Check Files
        for f in declaration.files:
            fp = Path(f)
            if not fp.is_absolute() and target_env.project_root:
                fp = Path(target_env.project_root) / f
            if not fp.exists():
                report.satisfied = False
                report.missing_files.append(str(fp))

        # 5. Check Directories
        for d in declaration.directories:
            dp = Path(d)
            if not dp.is_absolute() and target_env.project_root:
                dp = Path(target_env.project_root) / d
            if not dp.exists():
                report.satisfied = False
                report.missing_directories.append(str(dp))

        # 6. Check Credentials / Env Vars
        for cred in declaration.credentials + declaration.env_vars:
            val = os.environ.get(cred)
            if not val or val.startswith("your_") or val.strip() == "":
                report.satisfied = False
                report.missing_credentials.append(cred)

        if not report.satisfied:
            errors = []
            if report.missing_packages:
                errors.append(f"Missing packages: {', '.join(report.missing_packages)}")
            if report.missing_executables:
                errors.append(f"Missing executables: {', '.join(report.missing_executables)}")
            if report.missing_browser_binaries:
                errors.append(f"Missing browser binaries: {', '.join(report.missing_browser_binaries)}")
            if report.missing_credentials:
                errors.append(f"Missing credentials/env vars: {', '.join(report.missing_credentials)}")
            if report.missing_files:
                errors.append(f"Missing files: {', '.join(report.missing_files)}")
            report.error_summary = "; ".join(errors)

        return report

    def verify_python_import(self, module_name: str, env: EnvironmentProfile) -> Tuple[bool, str]:
        """
        Verify that a module can be imported cleanly inside the resolved target Python interpreter.
        Executes: resolved_python -c "import <mod>; print(getattr(<mod>, '__version__', 'ok'))"
        """
        if not env.executable or not Path(env.executable).exists():
            return False, "Interpreter not found"

        # Sanitize module name to avoid shell injection
        clean_mod = module_name.strip()
        if not re.match(r'^[a-zA-Z0-9_\.]+$', clean_mod):
            return False, "Invalid module name"

        check_code = f"import {clean_mod}; print(getattr({clean_mod}, '__version__', 'installed'))"
        
        env_vars = self.env_resolver.get_runtime_environment_vars(env)
        
        try:
            proc = subprocess.run(
                [env.executable, "-c", check_code],
                env=env_vars,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                ver = proc.stdout.strip()
                return True, ver or "installed"
            else:
                return False, proc.stderr.strip() or "ImportError"
        except Exception as e:
            return False, str(e)


_GLOBAL_DEPENDENCY_RESOLVER: Optional[DependencyResolver] = None


def get_dependency_resolver() -> DependencyResolver:
    global _GLOBAL_DEPENDENCY_RESOLVER
    if _GLOBAL_DEPENDENCY_RESOLVER is None:
        _GLOBAL_DEPENDENCY_RESOLVER = DependencyResolver()
    return _GLOBAL_DEPENDENCY_RESOLVER
