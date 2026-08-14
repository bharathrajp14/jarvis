"""Permission policy & deterministic security engine for BR JARVIS.

Enforces deterministic 6-tuple policy evaluation:
(User, Device, Application, Resource, Action, Risk) -> ActionDecision

Preserves historical top-level permissions interface for backwards compatibility:
- ALLOW_ALL permits every tool except explicit deny-list entries.
- CONFIRM_DESTRUCTIVE prompts for confirmation on destructive tools.
- CONFIRM_ALL only permits tools in ALWAYS_ALLOWED.
- DENY_ALL blocks everything except explicit allow-list entries.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Union

logger = logging.getLogger("JARVIS.Permissions")


class PermissionMode(str, Enum):
    ALLOW_ALL = "allow_all"
    CONFIRM_DESTRUCTIVE = "confirm_destructive"
    CONFIRM_ALL = "confirm_all"
    DENY_ALL = "deny_all"


class ActionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"
    ALLOW_FOR_SESSION = "allow_for_session"
    ALLOW_FOR_DEVICE = "allow_for_device"
    ALLOW_FOR_APPLICATION = "allow_for_application"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Tools that require confirmation under CONFIRM_DESTRUCTIVE mode
DESTRUCTIVE_TOOLS: FrozenSet[str] = frozenset(
    {
        "file_delete",
        "file_write",
        "run_code",
        "scratchpad_eval",
        "computer_settings",
        "system_cleanup",
        "system_optimizer",
        "process_kill",
        "run_automation_workflow",
        "execute_system_automation",
        "game_updater",
        "mobile_send_message",
        "mobile_delete_files",
    }
)


ALWAYS_ALLOWED: FrozenSet[str] = frozenset(
    {
        "help",
        "status",
        "memory_list",
        "memory_search",
        "file_read",
        "fetch_page",
        "fetch_raw",
        "web_search",
        "open_app",
        "browser_control",
        "keyboard_type",
        "keyboard_hotkey",
        "keyboard_press",
        "cursor_move",
        "cursor_click",
        "mouse_scroll",
        "focus_window",
        "screen_find",
        "screen_click",
        "smart_click",
    }
)


# Explicit permanent deny list for critical system resources
CRITICAL_RESOURCE_DENYLIST: FrozenSet[str] = frozenset({
    "system32", "winsxs", "registry", "sam", "security",
    "login data", ".ssh", ".gnupg", "id_rsa", "id_ed25519",
    "wallet.dat", ".pfx", "shadow", "/etc/passwd"
})


def _normalize_mode(value: str | None) -> PermissionMode:
    if not value:
        return PermissionMode.CONFIRM_DESTRUCTIVE
    try:
        return PermissionMode(value.strip().lower())
    except Exception:
        return PermissionMode.CONFIRM_DESTRUCTIVE


def _load_scope_defaults() -> dict[str, object]:
    scope_path = Path(__file__).resolve().parent / "current_scope.json"
    if not scope_path.exists():
        return {}
    try:
        with scope_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            permissions = payload.get("permissions", {})
            return permissions if isinstance(permissions, dict) else {}
    except Exception:
        pass
    return {}


@dataclass(slots=True)
class PolicyContext:
    """Represents the complete 6-tuple context for a security policy check."""
    user: str = "default_user"
    device: str = "pc_primary"
    application: str = "system"
    resource: str = ""
    action: str = ""
    risk: RiskLevel = RiskLevel.LOW
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PermissionPolicy:
    mode: PermissionMode = PermissionMode.CONFIRM_DESTRUCTIVE
    deny_names: FrozenSet[str] = field(default_factory=frozenset)
    allow_names: FrozenSet[str] = field(default_factory=frozenset)
    session_allowed_actions: set[str] = field(default_factory=set)

    def check(self, tool_name: str) -> bool:
        name = (tool_name or "").strip()
        if not name:
            return False
        if name in self.deny_names:
            return False
        if name in self.session_allowed_actions:
            return True
        if self.mode == PermissionMode.ALLOW_ALL:
            return True
        if self.mode == PermissionMode.CONFIRM_DESTRUCTIVE:
            # Allow everything except destructive tools (unless explicitly allowed)
            if name in DESTRUCTIVE_TOOLS and name not in self.allow_names:
                return False
            return True
        if self.mode == PermissionMode.CONFIRM_ALL:
            return name in ALWAYS_ALLOWED or name in self.allow_names
        if self.mode == PermissionMode.DENY_ALL:
            return name in self.allow_names
        return False

    def evaluate(self, ctx: PolicyContext) -> ActionDecision:
        """Deterministic 6-tuple evaluation engine."""
        action = (ctx.action or "").strip()
        resource_lower = (ctx.resource or "").lower().replace("\\", "/")

        # 1. Check critical resource denylist
        if any(bad in resource_lower for bad in CRITICAL_RESOURCE_DENYLIST):
            logger.warning("DENY: Resource '%s' matches critical security denylist.", ctx.resource)
            return ActionDecision.DENY

        # 2. Check explicit action denylist
        if action in self.deny_names:
            return ActionDecision.DENY

        # 3. Check session grant
        if action in self.session_allowed_actions:
            return ActionDecision.ALLOW_FOR_SESSION

        # 4. Evaluate based on Risk Level & Mode
        if ctx.risk == RiskLevel.CRITICAL:
            return ActionDecision.CONFIRM

        if self.mode == PermissionMode.DENY_ALL:
            return ActionDecision.ALLOW if action in self.allow_names else ActionDecision.DENY

        if self.mode == PermissionMode.ALLOW_ALL:
            return ActionDecision.ALLOW

        if self.mode == PermissionMode.CONFIRM_ALL:
            if action in ALWAYS_ALLOWED or action in self.allow_names:
                return ActionDecision.ALLOW
            return ActionDecision.CONFIRM

        # Default CONFIRM_DESTRUCTIVE
        if action in DESTRUCTIVE_TOOLS and action not in self.allow_names:
            return ActionDecision.CONFIRM

        if ctx.risk == RiskLevel.HIGH:
            return ActionDecision.CONFIRM

        return ActionDecision.ALLOW

    def grant_session_action(self, action: str) -> None:
        """Allow an action for the lifetime of the active session."""
        self.session_allowed_actions.add(action)


def _build_global_policy() -> PermissionPolicy:
    scope_defaults = _load_scope_defaults()
    env_value = os.environ.get("JARVIS_PERMISSION_MODE")
    env_mode = _normalize_mode(env_value) if env_value else None
    scope_raw = scope_defaults.get("mode") if isinstance(scope_defaults.get("mode"), str) else None
    scope_mode = _normalize_mode(scope_raw) if scope_raw else None

    mode = env_mode or scope_mode or PermissionMode.CONFIRM_DESTRUCTIVE
    logger.info("[Permissions] Active permission policy mode: %s", mode.value.upper())

    deny_tools = scope_defaults.get("deny_tools", [])
    if not isinstance(deny_tools, list):
        deny_tools = []

    allow_tools = scope_defaults.get("allow_tools", [])
    if not isinstance(allow_tools, list):
        allow_tools = []

    return PermissionPolicy(
        mode=mode,
        deny_names=frozenset(str(name) for name in deny_tools),
        allow_names=frozenset(str(name) for name in allow_tools),
    )


PERMISSIONS = _build_global_policy()


def check_permission(tool_name: str, args: dict | None = None) -> bool:
    """Check if tool execution is permitted under global policy and path security policies."""
    if not PERMISSIONS.check(tool_name):
        return False

    if args and isinstance(args, dict):
        for path_key in ("AbsolutePath", "TargetFile", "SearchPath", "file_path", "path"):
            val = args.get(path_key)
            if val and isinstance(val, (str, Path)):
                if not PathPolicy.allow_cloud_context(val):
                    return False
    return True


def evaluate_action_policy(
    action: str,
    resource: str = "",
    device: str = "pc_primary",
    application: str = "system",
    user: str = "default_user",
    risk: RiskLevel = RiskLevel.LOW,
    args: Optional[Dict[str, Any]] = None
) -> ActionDecision:
    """Public helper to evaluate a full 6-tuple policy decision."""
    ctx = PolicyContext(
        user=user,
        device=device,
        application=application,
        resource=resource,
        action=action,
        risk=risk,
        metadata=args or {}
    )
    return PERMISSIONS.evaluate(ctx)


# ── Path Policy & Tiered File Access ────────────────────────────────────────

class PathTier(Enum):
    TIER_0_WORKSPACE = 0
    TIER_1_USER_PROFILE = 1
    TIER_2_CRITICAL_SECRETS = 2


TIER_2_PATTERNS = frozenset({
    "system32", "winsxs", "registry", "sam", "system", "security",
    "login data", ".ssh", ".gnupg", "id_rsa", "id_ed25519", "wallet",
    ".pem", ".key", ".pfx", "shadow", "passwd"
})


class PathPolicy:
    """Evaluates file paths against Tier 0 (Workspace), Tier 1 (Profile), Tier 2 (Critical/Secrets)."""

    @classmethod
    def get_tier(cls, path_input: Union[str, Path]) -> PathTier:
        p_str = str(path_input).lower().replace("\\", "/")

        # Check Tier 2 Critical / Secrets
        if any(pat in p_str for pat in TIER_2_PATTERNS) or p_str.endswith((".pem", ".key", ".pfx")):
            return PathTier.TIER_2_CRITICAL_SECRETS

        # Check Tier 0 Workspace
        workspace_root = str(Path(".").resolve()).lower().replace("\\", "/")
        if p_str.startswith(workspace_root) or "br_workspace" in p_str or "documents/projects" in p_str:
            return PathTier.TIER_0_WORKSPACE

        # Default to Tier 1 User Profile
        return PathTier.TIER_1_USER_PROFILE

    @classmethod
    def allow_cloud_context(cls, path_input: Union[str, Path]) -> bool:
        """Return True if path is safe to send to cloud LLMs (Tier 0 or Tier 1). Return False for Tier 2."""
        tier = cls.get_tier(path_input)
        return tier != PathTier.TIER_2_CRITICAL_SECRETS


def cloud_context_exclusion_check(path_input: Union[str, Path]) -> bool:
    """Helper function to verify if file path is permitted in cloud prompt payload."""
    return PathPolicy.allow_cloud_context(path_input)
