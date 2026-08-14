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
from typing import FrozenSet, List, Optional, Set, Union

logger = logging.getLogger("JARVIS.PathPolicy")

# Critical OS and secret paths permanently denied
CRITICAL_RESOURCE_DENYLIST: FrozenSet[str] = frozenset({
    "system32", "winsxs", "registry", "sam", "security",
    "login data", ".ssh", ".gnupg", "id_rsa", "id_ed25519",
    "wallet.dat", ".pfx", "shadow", "passwd", "/etc/shadow",
    "/etc/sudoers", "/etc/passwd", "windows/system32", "windows/syswow64"
})

DENIED_EXTENSIONS: FrozenSet[str] = frozenset({
    ".pem", ".key", ".pfx", ".pkcs12", ".kdbx", ".wallet"
})


class PathTier(int, Enum):
    TIER_0_WORKSPACE        = 0  # Confined workspace directory (full access)
    TIER_1_USER_PROFILE     = 1  # User home directory / documents (requires user privilege)
    TIER_2_CRITICAL_SECRETS = 2  # Denied system & secret paths (blocked permanently)


class PathSecurityPolicy:
    """Evaluates and strictly normalizes all filesystem paths."""

    def __init__(
        self,
        workspace_root: Optional[Union[str, Path]] = None,
        allowed_roots: Optional[List[Union[str, Path]]] = None
    ):
        base = Path(workspace_root) if workspace_root else Path.cwd()
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
        """Resolve a raw path string into a strictly normalized canonical Path.
        Fails closed by raising PermissionError or ValueError on malformed paths.
        """
        if not raw_path:
            raise ValueError("Empty path cannot be canonicalized.")

        p_str = str(raw_path).strip()
        # Disallow UNC paths on Windows if they attempt network traversal
        if sys.platform == "win32" and (p_str.startswith(r"\\") or p_str.startswith("//")):
            if not p_str.startswith("\\\\?\\"):  # allow extended length if local
                raise PermissionError(f"UNC remote network paths are prohibited: {p_str}")


        # Expand user and environment variables
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
        try:
            resolved = self.canonicalize(path_input)
        except Exception:
            return False

        norm_str = str(resolved).lower().replace("\\", "/")

        # 1. Check extension denylist
        if resolved.suffix.lower() in DENIED_EXTENSIONS:
            return False

        # 2. Check path component denylist
        parts = [p.lower() for p in resolved.parts]
        for part in parts:
            if part in CRITICAL_RESOURCE_DENYLIST:
                return False

        for bad in CRITICAL_RESOURCE_DENYLIST:
            if bad in norm_str:
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
        """Return True if path is safe to send to cloud LLMs (Tier 0 or Tier 1). Return False for Tier 2."""
        tier = self.get_tier(path_input)
        return tier != PathTier.TIER_2_CRITICAL_SECRETS


_GLOBAL_PATH_POLICY: Optional[PathSecurityPolicy] = None


def get_path_policy() -> PathSecurityPolicy:
    global _GLOBAL_PATH_POLICY
    if _GLOBAL_PATH_POLICY is None:
        _GLOBAL_PATH_POLICY = PathSecurityPolicy()
    return _GLOBAL_PATH_POLICY
