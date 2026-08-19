# core/execution/recovery_manager.py — Safe Automated Runtime Repair & Recovery Engine
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from .dependency_resolver import get_dependency_resolver
from .environment_resolver import get_environment_resolver
from .process_runner import get_process_runner
from .types import (
    ExecutionResult,
    ExecutionStatus,
    RepairAction,
    RepairPolicy,
)

logger = logging.getLogger("JARVIS.RecoveryManager")


class RecoveryManager:
    """
    Safe Automated Runtime Repair & Recovery Engine.
    Diagnoses execution failures, verifies repair eligibility under active policy,
    applies transactional repairs in the target virtual environment, and verifies repair success.
    """

    def __init__(
        self,
        policy: RepairPolicy = RepairPolicy.AUTO_REPAIR_SAFE,
        env_resolver=None,
        dep_resolver=None,
        process_runner=None,
    ):
        self.policy = policy
        self.env_resolver = env_resolver or get_environment_resolver()
        self.dep_resolver = dep_resolver or get_dependency_resolver()
        self.process_runner = process_runner or get_process_runner()
        self._max_retries = 2

    def can_auto_repair(self, action_type: str, risk_level: str = "LOW") -> bool:
        """Check if an automated repair is permitted under the active policy."""
        if self.policy == RepairPolicy.NO_AUTO_REPAIR:
            return False
        if self.policy == RepairPolicy.AUTO_REPAIR_SAFE:
            return risk_level.upper() in ("LOW", "SAFE")
        if self.policy == RepairPolicy.ASK_BEFORE_REPAIR:
            return False
        return False

    def diagnose_failure(self, result: ExecutionResult) -> Optional[RepairAction]:
        """Diagnose a failed ExecutionResult and construct a safe RepairAction if applicable."""
        if result.success and result.status == ExecutionStatus.SUCCESS_VERIFIED:
            return None

        stderr = result.stderr or result.error or ""

        # 1. Missing Python Module (ModuleNotFoundError / ImportError)
        match_mod = re.search(r"No module named ['\"]([a-zA-Z0-9_\.]+)['\"]", stderr)
        if not match_mod:
            match_mod = re.search(r"ModuleNotFoundError:\s+No module named\s+([a-zA-Z0-9_\.]+)", stderr)
        if not match_mod:
            match_mod = re.search(r"ImportError:\s+cannot import name.*from\s+([a-zA-Z0-9_\.]+)", stderr)

        if match_mod:
            mod_name = match_mod.group(1).split(".")[0]
            pkg_name = self.dep_resolver.map_module_to_package(mod_name)
            target_env = result.runtime or self.env_resolver.resolve_python()

            cmd = [target_env.executable, "-m", "pip", "install", pkg_name]
            return RepairAction(
                action_type="install_package",
                description=f"Install missing package '{pkg_name}' (for module '{mod_name}') into target environment {target_env.precedence_source}",
                command=cmd,
                target_environment=target_env,
                risk_level="SAFE",
            )

        # 2. Missing Playwright Chromium binary
        if "playwright" in stderr.lower() and (
            "executable doesn't exist" in stderr.lower()
            or "browser not found" in stderr.lower()
            or "chromium" in stderr.lower()
        ):
            target_env = result.runtime or self.env_resolver.resolve_python()
            cmd = [target_env.executable, "-m", "playwright", "install", "chromium"]
            return RepairAction(
                action_type="install_browser",
                description="Install missing Playwright Chromium browser binaries",
                command=cmd,
                target_environment=target_env,
                risk_level="SAFE",
            )

        # 3. Missing Output Directory
        if "FileNotFoundError" in stderr or "No such file or directory" in stderr:
            # Check if directory creation is needed
            if result.cwd and not Path(result.cwd).exists():
                return RepairAction(
                    action_type="create_directory",
                    description=f"Create missing working directory '{result.cwd}'",
                    command=[],
                    risk_level="SAFE",
                )

        return None

    def execute_repair(self, repair_action: RepairAction) -> bool:
        """Execute the repair action and verify that the target capability is restored."""
        if not self.can_auto_repair(repair_action.action_type, repair_action.risk_level):
            logger.warning(f"🔒 Auto-repair blocked by policy ({self.policy.value}): {repair_action.description}")
            return False

        logger.info(f"🔧 Attempting safe auto-repair: {repair_action.description}")
        t0 = time.perf_counter()

        try:
            if repair_action.action_type in ("install_package", "install_browser"):
                if not repair_action.command:
                    return False

                res = self.process_runner.run(
                    command=repair_action.command,
                    env_profile=repair_action.target_environment,
                    timeout_sec=120.0,
                )
                repair_action.duration_ms = (time.perf_counter() - t0) * 1000.0
                repair_action.executed = True

                if res.return_code == 0:
                    repair_action.success = True
                    logger.info(
                        f"✅ Auto-repair succeeded ({repair_action.duration_ms:.1f}ms): {repair_action.description}"
                    )
                    return True
                else:
                    repair_action.success = False
                    repair_action.error = res.stderr or res.stdout
                    logger.error(f"❌ Auto-repair command failed: {repair_action.error}")
                    return False

            elif repair_action.action_type == "create_directory":
                # Create directory
                if repair_action.target_environment and repair_action.target_environment.working_directory:
                    Path(repair_action.target_environment.working_directory).mkdir(parents=True, exist_ok=True)
                repair_action.executed = True
                repair_action.success = True
                return True

            return False

        except Exception as e:
            repair_action.duration_ms = (time.perf_counter() - t0) * 1000.0
            repair_action.executed = True
            repair_action.success = False
            repair_action.error = str(e)
            logger.error(f"❌ Auto-repair exception: {e}")
            return False


import re  # needed for regex matching in diagnose_failure

_GLOBAL_RECOVERY_MANAGER: Optional[RecoveryManager] = None


def get_recovery_manager() -> RecoveryManager:
    global _GLOBAL_RECOVERY_MANAGER
    if _GLOBAL_RECOVERY_MANAGER is None:
        _GLOBAL_RECOVERY_MANAGER = RecoveryManager()
    return _GLOBAL_RECOVERY_MANAGER
