# security/path_policy.py — Canonical Filesystem Path Policy & Boundary Enforcement
"""
Deterministic path validation and sandbox boundary enforcement for BR JARVIS.
Handles path normalization, symlink resolution, Windows junction points,
UNC paths, and tiered boundary checks.
"""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import FrozenSet, List, Optional, Union

logger = logging.getLogger("JARVIS.PathPolicy")

CRITICAL_RESOURCE_DENYLIST: FrozenSet[str] = frozenset(
    {
        "system32",
        "syswow64",
        "winsxs",
        "registry",
        "sam",
        "security",
        "login data",
        ".ssh",
        ".gnupg",
        ".aws",
        "credentials",
        "id_rsa",
        "id_ed25519",
        "id_dsa",
        "wallet.dat",
        ".pfx",
        "shadow",
        "passwd",
        "etc/shadow",
        "etc/sudoers",
        "etc/passwd",
        "windows/system32",
        "windows/syswow64",
        "windows/win.ini",
        "win.ini",
        "system.ini",
        "boot.ini",
        ".env",
        ".env.local",
        ".env.production",
        ".git",
        ".npmrc",
        ".pypirc",
        "secrets.json",
        "secrets.yaml",
        "secrets.env",
    }
)

DENIED_EXTENSIONS: FrozenSet[str] = frozenset({".pem", ".key", ".pfx", ".pkcs12", ".kdbx", ".wallet", ".crt", ".cer"})


class PathTier(int, Enum):
    TIER_0_WORKSPACE = 0  # Confined workspace directory (full access)
    TIER_1_USER_PROFILE = 1  # User home directory / documents (requires user privilege)
    TIER_2_CRITICAL_SECRETS = 2  # Denied system & secret paths (blocked permanently)


class PathSecurityPolicy:
    """Evaluates and strictly normalizes all filesystem paths."""

    def __init__(
        self,
        workspace_root: Optional[Union[str, Path]] = None,
        allowed_roots: Optional[List[Union[str, Path]]] = None,
    ):
        if workspace_root:
            base = Path(workspace_root)
        else:
            from brjarvis.core.paths import paths

            base = paths.WORKSPACE_ROOT
        try:
            self.workspace_root = base.resolve()
        except Exception:
            self.workspace_root = base.absolute()

        self.allowed_roots: List[Path] = [self.workspace_root]
        if allowed_roots:
            for r in allowed_roots:
                try:
                    self.allowed_roots.append(Path(r).resolve())
                except Exception:
                    pass

    def canonicalize(self, raw_path: Union[str, Path]) -> Path:
        """Resolve a raw path string into a strictly normalized canonical Path."""
        if not raw_path:
            raise ValueError("Empty path cannot be canonicalized.")

        p_str = str(raw_path).strip()
        if sys.platform == "win32" and (p_str.startswith(r"\\") or p_str.startswith("//")):
            if not p_str.startswith("\\\\?\\"):
                raise PermissionError(f"UNC remote network paths are prohibited: {p_str}")

        expanded = os.path.expandvars(os.path.expanduser(p_str))
        target_path = Path(expanded)

        try:
            resolved = target_path.resolve(strict=False)
        except Exception as e:
            logger.warning("Path resolution error for '%s': %s", raw_path, e)
            raise PermissionError(f"Unsafe path resolution failed: {raw_path}") from e

        return resolved

    def is_safe_resource(self, path_input: Union[str, Path]) -> bool:
        """Check if path does not violate critical security deny lists."""
        if not path_input:
            return False

        raw_str = str(path_input).strip().lower().replace("\\", "/")

        # Direct string check on raw input for critical secrets or traversal
        for bad in CRITICAL_RESOURCE_DENYLIST:
            if bad in raw_str:
                return False

        if raw_str.startswith(".env") or "/.env" in raw_str:
            return False

        try:
            resolved = self.canonicalize(path_input)
        except Exception:
            return False

        norm_str = str(resolved).lower().replace("\\", "/")

        # Check extension denylist
        if resolved.suffix.lower() in DENIED_EXTENSIONS:
            return False

        # Check filename and path components
        name_lower = resolved.name.lower()
        if name_lower in CRITICAL_RESOURCE_DENYLIST or name_lower.startswith(".env"):
            return False

        parts = [p.lower() for p in resolved.parts]
        for part in parts:
            if part in CRITICAL_RESOURCE_DENYLIST or part.startswith(".env"):
                return False

        for bad in CRITICAL_RESOURCE_DENYLIST:
            if bad in norm_str:
                return False

        # Check Windows root and system root directory accesses
        if sys.platform == "win32":
            win_dir = os.environ.get("WINDIR", r"C:\Windows").lower().replace("\\", "/")
            if norm_str.startswith(win_dir) or "/windows/" in norm_str or norm_str.endswith("/windows"):
                # Prohibit access to Windows directory
                return False

        return True

    def get_tier(self, path_input: Union[str, Path]) -> PathTier:
        """Determine path security tier."""
        if not self.is_safe_resource(path_input):
            return PathTier.TIER_2_CRITICAL_SECRETS

        try:
            resolved = self.canonicalize(path_input)
        except Exception:
            return PathTier.TIER_2_CRITICAL_SECRETS

        # Check Tier 0 Workspace
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                return PathTier.TIER_0_WORKSPACE
            except ValueError:
                continue

        # Check Tier 1 User Profile
        try:
            user_home = Path.home().resolve()
            resolved.relative_to(user_home)
            return PathTier.TIER_1_USER_PROFILE
        except Exception:
            pass

        return PathTier.TIER_1_USER_PROFILE

    def is_within_workspace(self, path_input: Union[str, Path]) -> bool:
        """Verify that the target path is strictly confined inside workspace root."""
        tier = self.get_tier(path_input)
        return tier == PathTier.TIER_0_WORKSPACE

    def allow_cloud_context(self, path_input: Union[str, Path]) -> bool:
        tier = self.get_tier(path_input)
        return tier != PathTier.TIER_2_CRITICAL_SECRETS

    def is_sandbox_internal_path(self, path_input: Union[str, Path]) -> bool:
        if not path_input:
            return False
        p_str = str(path_input).replace("\\", "/").lower()
        return (
            "jarvis_sandbox_jails" in p_str
            or "sandbox_jails" in p_str
            or "/jail_" in p_str
            or "\\jail_" in str(path_input).lower()
        )

    def validate_artifact_export_path(
        self, source: Union[str, Path], destination: Union[str, Path], host_root: Union[str, Path]
    ) -> bool:
        try:
            dest_res = Path(destination).resolve(strict=False)
            root_res = Path(host_root).resolve(strict=False)
            dest_res.relative_to(root_res)
            return self.is_safe_resource(dest_res)
        except Exception:
            return False


def is_sandbox_internal_path(path_input: Union[str, Path]) -> bool:
    if not path_input:
        return False
    p_str = str(path_input).replace("\\", "/").lower()
    return (
        "jarvis_sandbox_jails" in p_str
        or "sandbox_jails" in p_str
        or "/jail_" in p_str
        or "\\jail_" in str(path_input).lower()
    )


_GLOBAL_PATH_POLICY: Optional[PathSecurityPolicy] = None


def get_path_policy() -> PathSecurityPolicy:
    global _GLOBAL_PATH_POLICY
    if _GLOBAL_PATH_POLICY is None:
        _GLOBAL_PATH_POLICY = PathSecurityPolicy()
    return _GLOBAL_PATH_POLICY
