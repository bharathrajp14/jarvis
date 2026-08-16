"""Unit tests for Path Authority and Workspace Lifecycle Manager."""
from __future__ import annotations

import os
from pathlib import Path
import pytest

from brjarvis.core.paths import paths, find_project_root, find_python_executable, PathManager


@pytest.mark.unit
def test_project_root_detection():
    """Verify project root contains start.py or pyproject.toml."""
    root = find_project_root()
    assert root.exists()
    assert (root / "start.py").exists() or (root / "pyproject.toml").exists() or (root / "src").exists()


@pytest.mark.unit
def test_path_manager_singleton_hierarchy():
    """Verify paths singleton resolves canonical paths correctly."""
    assert paths.PROJECT_ROOT.exists()
    assert paths.SOURCE_ROOT.exists()
    assert str(paths.SOURCE_ROOT).endswith("brjarvis")
    assert paths.APPS_ROOT.exists()
    assert paths.CONFIG_ROOT.exists()
    assert paths.WORKSPACE_ROOT.exists()
    assert paths.RUNTIME_ROOT.exists()


@pytest.mark.unit
def test_path_manager_ensure_directories(tmp_path):
    """Verify PathManager ensures all required subdirectories exist."""
    custom_root = tmp_path / "custom_project"
    custom_root.mkdir(parents=True, exist_ok=True)
    pm = PathManager(root=custom_root)
    
    assert pm.DOCUMENTS_DIR.exists()
    assert pm.RESUMES_DIR.exists()
    assert pm.CAREER_DIR.exists()
    assert pm.LOG_ROOT.exists()
    assert pm.CAPTURE_ROOT.exists()
    assert pm.REPORT_ROOT.exists()
    assert pm.STATE_ROOT.exists()
