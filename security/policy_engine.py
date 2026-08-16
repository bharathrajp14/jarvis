# security/policy_engine.py — Deterministic 6-Tuple Policy Engine
"""
Deterministic Fail-Closed Policy Engine for BR JARVIS.
Evaluates 6-tuple context: (User, Session, Device, Target/Resource, Capability, Risk) -> ActionDecision.
Guarantees that policy evaluation failure fails CLOSED (DENY).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Set, Union

from security.capabilities import Capability, RiskLevel
from security.path_policy import CRITICAL_RESOURCE_DENYLIST, PathTier, get_path_policy

logger = logging.getLogger("JARVIS.PolicyEngine")


class PermissionMode(str, Enum):
    ALLOW_ALL           = "allow_all"
    CONFIRM_DESTRUCTIVE = "confirm_destructive"
    CONFIRM_ALL         = "confirm_all"
    DENY_ALL            = "deny_all"


class ActionDecision(str, Enum):
    ALLOW                 = "allow"
    DENY                  = "deny"
    CONFIRM               = "confirm"
    ALLOW_FOR_SESSION     = "allow_for_session"
    ALLOW_FOR_DEVICE      = "allow_for_device"
    ALLOW_FOR_APPLICATION = "allow_for_application"


# Default dangerous tools requiring explicit user confirmation under CONFIRM_DESTRUCTIVE mode
DESTRUCTIVE_TOOLS: FrozenSet[str] = frozenset({
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
    "application_submit",
    "submit_job_application",
    "canva_oauth_connect",
})

# Safe, read-only informative tools that carry zero side-effects
ALWAYS_ALLOWED_SAFE: FrozenSet[str] = frozenset({
    "help",
    "status",
    "memory_list",
    "memory_search",
    "file_read",
    "fetch_page",
    "fetch_raw",
    "web_search",
    "artifact_export",
    "artifact_list",
    "career_profile_get",
    "job_search",
    "job_match",
    "job_details",
    "ats_score_resume",
    "career_analytics_summary",
    "interview_prep_generate",
})


@dataclass(slots=True)
class PolicyContext:
    """Represents the complete 6-tuple context for a security policy check."""
    user: str = "default_user"
    session_id: str = "default_session"
    device: str = "pc_primary"
    application: str = "system"
    resource: str = ""
    action: str = ""
    capabilities: Set[Capability] = field(default_factory=set)
    risk: RiskLevel = RiskLevel.LOW
    metadata: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """Authoritative deterministic policy engine enforcing fail-closed capability security."""

    def __init__(
        self,
        mode: PermissionMode = PermissionMode.CONFIRM_DESTRUCTIVE,
        deny_names: Optional[FrozenSet[str]] = None,
        allow_names: Optional[FrozenSet[str]] = None,
    ):
        self.mode = mode
        self.deny_names = deny_names or frozenset()
        self.allow_names = allow_names or frozenset()
        self.session_grants: Dict[str, Set[str]] = {}  # session_id -> set of granted actions/capabilities
        self.path_policy = get_path_policy()

    def grant_session_action(self, action_or_capability: str, session_id: str = "default_session") -> None:
        """Grant permission for a specific action or capability for the duration of the session."""
        if session_id not in self.session_grants:
            self.session_grants[session_id] = set()
        self.session_grants[session_id].add(action_or_capability)
        logger.info("Granted session action '%s' for session '%s'", action_or_capability, session_id)

    def revoke_session_grants(self, session_id: str = "default_session") -> None:
        """Clear all temporary session grants."""
        if session_id in self.session_grants:
            self.session_grants[session_id].clear()

    def evaluate(self, ctx: PolicyContext) -> ActionDecision:
        """Deterministic 6-tuple evaluation engine.
        Guarantees FAIL-CLOSED: if any exception occurs, returns ActionDecision.DENY.
        """
        try:
            return self._evaluate_internal(ctx)
        except Exception as exc:
            logger.error("Security policy evaluation error (failing CLOSED to DENY): %s", exc, exc_info=True)
            return ActionDecision.DENY

    def _evaluate_internal(self, ctx: PolicyContext) -> ActionDecision:
        action = (ctx.action or "").strip()
        resource = (ctx.resource or "").strip()
        session_id = ctx.session_id or "default_session"
        grants = self.session_grants.get(session_id, set())

        # 1. Resource path security check
        if resource:
            if not self.path_policy.is_safe_resource(resource):
                logger.warning("DENY: Resource '%s' matches critical security denylist.", resource)
                return ActionDecision.DENY

        # 2. Check explicit action denylist
        if action in self.deny_names:
            logger.info("DENY: Action '%s' matches explicit deny names.", action)
            return ActionDecision.DENY

        # 3. Check session grant
        if action in grants or any(cap.value in grants for cap in ctx.capabilities):
            return ActionDecision.ALLOW_FOR_SESSION

        # 4. Critical Risk operations ALWAYS require explicit user confirmation
        if ctx.risk == RiskLevel.CRITICAL:
            return ActionDecision.CONFIRM

        # 5. Dangerous capabilities (Code Execution, System Control, Destructive)
        high_risk_caps = {
            Capability.CODE_EXECUTION,
            Capability.SYSTEM_CONTROL,
            Capability.DESTRUCTIVE,
            Capability.FINANCIAL,
            Capability.CREDENTIAL_ACCESS
        }
        if any(cap in high_risk_caps for cap in ctx.capabilities):
            if self.mode == PermissionMode.DENY_ALL and action not in self.allow_names:
                return ActionDecision.DENY
            if action not in self.allow_names:
                return ActionDecision.CONFIRM

        # 6. Evaluate by Permission Mode
        if self.mode == PermissionMode.DENY_ALL:
            return ActionDecision.ALLOW if action in self.allow_names else ActionDecision.DENY

        if self.mode == PermissionMode.ALLOW_ALL:
            # Even in allow_all, critical risk requires confirmation
            return ActionDecision.ALLOW

        if self.mode == PermissionMode.CONFIRM_ALL:
            if action in ALWAYS_ALLOWED_SAFE or action in self.allow_names:
                return ActionDecision.ALLOW
            return ActionDecision.CONFIRM

        # Default: CONFIRM_DESTRUCTIVE
        if action in DESTRUCTIVE_TOOLS and action not in self.allow_names:
            return ActionDecision.CONFIRM

        if ctx.risk == RiskLevel.HIGH and action not in self.allow_names:
            return ActionDecision.CONFIRM

        return ActionDecision.ALLOW

    def check_tool_permission(self, tool_name: str, args: Optional[Dict[str, Any]] = None, session_id: str = "default_session") -> bool:
        """Fast helper to check if tool execution is authorized under active policy.
        Fails CLOSED on any error.
        """
        try:
            name = (tool_name or "").strip()
            if not name:
                return False

            # Extract potential path resources from arguments
            resource = ""
            if args and isinstance(args, dict):
                for key in ("AbsolutePath", "TargetFile", "SearchPath", "file_path", "path", "target", "cwd"):
                    val = args.get(key)
                    if val and isinstance(val, (str, Path)):
                        resource = str(val)
                        break

            # Map known tool capabilities
            caps: Set[Capability] = set()
            risk = RiskLevel.LOW
            if name in ("run_code", "scratchpad_eval"):
                caps.add(Capability.CODE_EXECUTION)
                risk = RiskLevel.HIGH
            elif name in ("file_write", "file_delete"):
                caps.add(Capability.FILE_MUTATION)
                caps.add(Capability.DESTRUCTIVE)
                risk = RiskLevel.HIGH
            elif name in ("computer_settings", "process_kill", "system_cleanup"):
                caps.add(Capability.SYSTEM_CONTROL)
                risk = RiskLevel.HIGH
            elif name.startswith("keyboard_") or name.startswith("cursor_") or name.startswith("mouse_") or name == "open_app":
                caps.add(Capability.DESKTOP_CONTROL)
                risk = RiskLevel.MEDIUM
            elif name in ALWAYS_ALLOWED_SAFE:
                caps.add(Capability.READ_ONLY)
                risk = RiskLevel.LOW

            ctx = PolicyContext(
                session_id=session_id,
                action=name,
                resource=resource,
                capabilities=caps,
                risk=risk,
                metadata=args or {}
            )

            decision = self.evaluate(ctx)
            return decision in (ActionDecision.ALLOW, ActionDecision.ALLOW_FOR_SESSION)
        except Exception as e:
            logger.error("check_tool_permission failed closed (DENY): %s", e)
            return False


_GLOBAL_POLICY_ENGINE: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    global _GLOBAL_POLICY_ENGINE
    if _GLOBAL_POLICY_ENGINE is None:
        _GLOBAL_POLICY_ENGINE = PolicyEngine()
    return _GLOBAL_POLICY_ENGINE


SecurityPolicyEngine = PolicyEngine
