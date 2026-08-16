"""
Tests for WorkspaceManager path resolution — MK40.2 §11/§12

Verifies:
  - resolve_workspace_path() normalizes relative paths to workspace_root
  - PathContainmentError raised on double-root paths (workspace/workspace/)
  - PathContainmentError raised on path traversal attempts
  - Absolute paths within workspace pass through
"""
from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def wm(tmp_path):
    """Create a WorkspaceManager with a tmp workspace root."""
    from brjarvis.core.paths import PathManager, WorkspaceManager

    # Build a minimal PathManager pointing to tmp_path
    pm = PathManager.__new__(PathManager)
    pm.PROJECT_ROOT  = tmp_path / "project"
    pm.WORKSPACE_ROOT = tmp_path / "workspace"
    pm.DOCUMENTS_DIR  = pm.WORKSPACE_ROOT / "Documents"
    pm.ARTIFACT_ROOT  = pm.WORKSPACE_ROOT / "artifacts"
    pm.CAREER_DIR     = pm.WORKSPACE_ROOT / "Career"
    pm.TEMP_ROOT      = pm.WORKSPACE_ROOT / "Temporary"
    # Create the directories
    for d in [pm.PROJECT_ROOT, pm.WORKSPACE_ROOT, pm.DOCUMENTS_DIR,
              pm.ARTIFACT_ROOT, pm.CAREER_DIR, pm.TEMP_ROOT]:
        d.mkdir(parents=True, exist_ok=True)

    return WorkspaceManager(pm=pm)


@pytest.mark.unit
def test_relative_path_resolves_under_workspace(wm):
    """Relative paths must resolve under workspace_root."""
    resolved = wm.resolve_workspace_path("Portfolio")
    assert resolved == (wm.workspace_root / "Portfolio").resolve()
    assert str(wm.workspace_root) in str(resolved)


@pytest.mark.unit
def test_double_root_workspace_raises_error(wm):
    """
    MK40.2 §12: workspace/workspace/Portfolio must raise PathContainmentError.
    This is the documented bug from the MK40.2 spec.
    """
    from brjarvis.core.paths import PathContainmentError

    with pytest.raises(PathContainmentError, match="Duplicated workspace root"):
        wm.resolve_workspace_path("workspace/workspace/Portfolio")


@pytest.mark.unit
def test_path_traversal_raises_error(wm):
    """Paths that traverse outside workspace_root must be rejected."""
    from brjarvis.core.paths import PathContainmentError

    with pytest.raises(PathContainmentError):
        wm.resolve_workspace_path("../../etc/passwd")


@pytest.mark.unit
def test_absolute_path_within_workspace_passes(wm):
    """Absolute paths inside workspace_root must be accepted."""
    target = wm.workspace_root / "Documents" / "resume.docx"
    resolved = wm.resolve_workspace_path(str(target))
    assert resolved == target.resolve()


@pytest.mark.unit
def test_absolute_path_outside_workspace_raises(wm):
    """Absolute paths outside workspace_root must be rejected."""
    from brjarvis.core.paths import PathContainmentError

    outside = Path("/tmp/malicious_file.txt")
    with pytest.raises(PathContainmentError):
        wm.resolve_workspace_path(str(outside))


@pytest.mark.unit
def test_nested_relative_path_resolves_correctly(wm):
    """Nested relative paths like Documents/Portfolio/index.html must resolve correctly."""
    resolved = wm.resolve_workspace_path("Documents/Portfolio/index.html")
    expected = (wm.workspace_root / "Documents" / "Portfolio" / "index.html").resolve()
    assert resolved == expected


@pytest.mark.unit
def test_workspace_root_dot_passes(wm):
    """'.' should resolve to workspace_root itself."""
    resolved = wm.resolve_workspace_path(".")
    assert resolved == wm.workspace_root.resolve()
