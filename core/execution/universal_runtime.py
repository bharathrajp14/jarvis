# core/execution/universal_runtime.py — Master Universal Execution Runtime Engine
from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from core.execution.capability_checker import CapabilityChecker, get_capability_checker
from core.execution.completion_gate import TaskCompletionGate, get_task_completion_gate
from core.execution.dependency_resolver import DependencyResolver, get_dependency_resolver
from core.execution.environment_resolver import EnvironmentResolver, get_environment_resolver
from core.execution.process_runner import ProcessRunner, get_process_runner
from core.execution.recovery_manager import RecoveryManager, get_recovery_manager
from core.execution.trace import ExecutionTrace
from core.execution.types import (
    DependencyDeclaration,
    EnvironmentProfile,
    ExecutionResult,
    ExecutionStatus,
    RepairPolicy,
    RuntimeType,
    VerificationOutcome,
)
from core.execution.verifier import UniversalVerifier, get_universal_verifier

logger = logging.getLogger("JARVIS.UniversalExecutionRuntime")


class UniversalExecutionRuntime:
    """
    Master Universal Execution Runtime Engine for BR JARVIS MK40.2.
    
    Orchestrates:
    - 6-Tier Deterministic Environment Resolution
    - Machine-Readable Universal Dependency Engine & Import Intelligence
    - Capability Preflight Verification
    - Process Tree Containment & Subprocess Lifecycle Management
    - Universal Side-Effect Verifiers & Semantic Output Validation
    - Safe Automated Runtime Repair & Recovery Workflows
    - Centralized Task Completion Gate preventing false-success claims
    - Developer Execution Tracing & Telemetry
    """

    _INSTANCE: Optional[UniversalExecutionRuntime] = None

    def __init__(
        self,
        default_project_root: Optional[Path | str] = None,
        repair_policy: RepairPolicy = RepairPolicy.AUTO_REPAIR_SAFE,
    ):
        self.env_resolver: EnvironmentResolver = get_environment_resolver(default_project_root)
        self.dep_resolver: DependencyResolver = get_dependency_resolver()
        self.capability_checker: CapabilityChecker = get_capability_checker()
        self.process_runner: ProcessRunner = get_process_runner()
        self.verifier: UniversalVerifier = get_universal_verifier()
        self.recovery_mgr: RecoveryManager = get_recovery_manager()
        self.recovery_mgr.policy = repair_policy
        self.completion_gate: TaskCompletionGate = get_task_completion_gate()

        logger.info("⚡ UniversalExecutionRuntime initialized")

    @classmethod
    def get_instance(cls, default_project_root: Optional[Path | str] = None) -> UniversalExecutionRuntime:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls(default_project_root)
        return cls._INSTANCE

    # ── 1. Code Execution ───────────────────────────────────────────────────

    def execute_code(
        self,
        code: str,
        lang: str = "python",
        cwd: Optional[Path | str] = None,
        timeout_sec: float = 30.0,
        extra_env: Optional[Dict[str, str]] = None,
        auto_repair: bool = True,
        trace: Optional[ExecutionTrace] = None,
        export_artifacts: bool = True,
    ) -> ExecutionResult:
        """
        Execute code in an isolated environment with preflight dependency checks,
        correct virtualenv interpreter resolution, auto-repair, and output validation.
        """
        lang = lang.lower().strip()
        t0 = time.perf_counter()

        if trace:
            trace.add_event("EXECUTION", f"Executing {lang} code ({len(code)} chars)", {"lang": lang, "timeout": timeout_sec})

        # Strip markdown code blocks if present
        clean_code = code.strip()
        clean_code = re.sub(r"^```[a-zA-Z0-9_\-]*\n?", "", clean_code)
        clean_code = re.sub(r"\n?```$", "", clean_code).strip()

        # 1. Environment Resolution
        if lang == "python":
            env_prof = self.env_resolver.resolve_python()
        elif lang in ("javascript", "node", "js"):
            env_prof = self.env_resolver.resolve_node()
        elif lang in ("powershell", "ps1"):
            env_prof = self.env_resolver.resolve_powershell()
        else:
            env_prof = self.env_resolver.resolve_python()

        if trace:
            trace.add_event("ENVIRONMENT", f"Resolved runtime: {env_prof.runtime_type.value} ({env_prof.precedence_source}) -> {env_prof.executable}")

        # 2. Dependency Preflight Check (Python)
        if lang == "python":
            imports = self.dep_resolver.extract_python_imports(clean_code)
            if imports:
                decl = DependencyDeclaration(runtime=RuntimeType.PYTHON, import_names=list(imports))
                dep_report = self.dep_resolver.verify_dependencies(decl, env=env_prof)
                if not dep_report.satisfied:
                    if trace:
                        trace.add_event("DEPENDENCY", f"Missing imports: {dep_report.error_summary}")
                    if auto_repair and dep_report.missing_packages:
                        for pkg in dep_report.missing_packages:
                            repair_act = self.recovery_mgr.diagnose_failure(
                                ExecutionResult(stderr=f"No module named '{pkg}'", runtime=env_prof)
                            )
                            if repair_act and self.recovery_mgr.execute_repair(repair_act):
                                if trace:
                                    trace.add_event("RECOVERY", f"Auto-repaired package '{pkg}' in {env_prof.executable}")

        # 3. Create isolated script file in jail directory
        jail_dir = Path(tempfile.gettempdir()) / "jarvis_runtime_jails" / f"jail_{uuid.uuid4().hex[:10]}"
        jail_dir.mkdir(parents=True, exist_ok=True)
        
        ext_map = {"python": ".py", "javascript": ".js", "powershell": ".ps1", "bash": ".sh"}
        script_file = jail_dir / f"main{ext_map.get(lang, '.py')}"
        script_file.write_text(clean_code, encoding="utf-8")

        # Resolve command
        if lang == "python":
            cmd = [env_prof.executable, str(script_file)]
        elif lang == "javascript":
            cmd = ["node", str(script_file)]
        elif lang == "powershell":
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script_file)]
        else:
            cmd = [env_prof.executable, str(script_file)]

        # 4. Execute via ProcessRunner
        exec_cwd = cwd or jail_dir
        result = self.process_runner.run(
            command=cmd,
            cwd=exec_cwd,
            env_profile=env_prof,
            extra_env=extra_env,
            timeout_sec=timeout_sec,
        )

        # 5. Handle Recovery if execution failed due to missing module
        if not result.success and auto_repair:
            repair_action = self.recovery_mgr.diagnose_failure(result)
            if repair_action and self.recovery_mgr.execute_repair(repair_action):
                if trace:
                    trace.add_event("RECOVERY", f"Retrying code execution after repair: {repair_action.description}")
                # Retry execution
                result = self.process_runner.run(
                    command=cmd,
                    cwd=exec_cwd,
                    env_profile=env_prof,
                    extra_env=extra_env,
                    timeout_sec=timeout_sec,
                )
                result.recovery = repair_action

        # 6. Export artifacts generated in jail before cleanup
        if export_artifacts and jail_dir.exists():
            try:
                from agent.artifacts import get_artifact_manager
                mgr = get_artifact_manager()
                for p in jail_dir.rglob("*"):
                    if p.is_file() and p.name not in ("main.py", "main.js", "main.ps1", "main.sh"):
                        rec = mgr.export_sandbox_artifact(p, task_id=jail_dir.name)
                        if rec.exported:
                            result.artifacts.append(rec.to_dict())
                            result.host_artifacts.append(rec.host_path)
            except Exception as art_err:
                logger.debug("Artifact auto-export note: %s", art_err)

        # 7. Output Contract Validation
        out_val = self.verifier.validate_output(result.stdout or result.stderr, return_code=result.return_code)
        if not out_val.verified and result.success:
            result.status = ExecutionStatus.FAILED
            result.error = out_val.details

        # 8. Clean up jail directory
        try:
            import shutil
            shutil.rmtree(jail_dir, ignore_errors=True)
        except Exception:
            pass

        if trace:
            trace.add_event("VALIDATION", f"Code execution finished with status {result.status.value}")

        return result

    # ── 2. Tool Execution Governance ────────────────────────────────────────

    def execute_tool_with_governance(
        self,
        tool_name: str,
        handler: Callable[[Dict[str, Any]], Any],
        args: Dict[str, Any],
        declaration: Optional[DependencyDeclaration] = None,
        auto_repair: bool = True,
        trace: Optional[ExecutionTrace] = None,
    ) -> ExecutionResult:
        """
        Execute any registered tool with full capability preflight, permission check,
        execution capture, and post-execution physical state verification.
        """
        t0 = time.perf_counter()
        if trace:
            trace.add_event("TOOL", f"Executing tool '{tool_name}' with args {list(args.keys())}")

        # 1. Dependency Preflight if declared
        if declaration:
            env_prof = self.env_resolver.resolve_python()
            dep_report = self.dep_resolver.verify_dependencies(declaration, env=env_prof)
            if not dep_report.satisfied:
                if trace:
                    trace.add_event("DEPENDENCY", f"Tool '{tool_name}' missing dependencies: {dep_report.error_summary}")
                if auto_repair and dep_report.missing_packages:
                    for pkg in dep_report.missing_packages:
                        repair_act = self.recovery_mgr.diagnose_failure(
                            ExecutionResult(stderr=f"No module named '{pkg}'", runtime=env_prof)
                        )
                        if repair_act and self.recovery_mgr.execute_repair(repair_act):
                            if trace:
                                trace.add_event("RECOVERY", f"Auto-repaired dependency '{pkg}' for tool '{tool_name}'")

        # 2. Invoke Handler
        try:
            import inspect
            if inspect.iscoroutinefunction(handler):
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(handler(args), loop)
                    raw_res = future.result(timeout=60.0)
                except RuntimeError:
                    raw_res = asyncio.run(handler(args))
            else:
                raw_res = handler(args)

            duration_ms = (time.perf_counter() - t0) * 1000.0
            str_output = str(raw_res)

            # 3. Post-execution physical side-effect verification
            v_outcome = self.verifier.verify_execution(tool_name, args, str_output, return_code=0)
            
            status = v_outcome.status
            if not v_outcome.verified:
                status = ExecutionStatus.VERIFICATION_FAILED

            if trace:
                trace.add_event("VERIFICATION", f"Verified side effects for '{tool_name}': {v_outcome.details}")

            return ExecutionResult(
                status=status,
                tool_or_command=tool_name,
                return_code=0 if v_outcome.verified else 1,
                stdout=str_output,
                output=raw_res,
                evidence=v_outcome.evidence or f"Executed tool '{tool_name}'",
                verification=v_outcome,
                duration_ms=duration_ms,
                error=v_outcome.error if not v_outcome.verified else None,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.error(f"❌ Error executing tool '{tool_name}': {e}", exc_info=True)
            if trace:
                trace.add_event("VALIDATION", f"Tool '{tool_name}' raised exception: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                tool_or_command=tool_name,
                return_code=1,
                stderr=str(e),
                output=f"Error executing tool '{tool_name}': {e}",
                error=str(e),
                duration_ms=duration_ms,
            )

    # ── 3. Diagnostics & Telemetry ─────────────────────────────────────────

    def diagnose_runtime(self) -> Dict[str, Any]:
        """Perform active capability diagnostics across all runtime subsystems."""
        py_prof = self.env_resolver.resolve_python()
        node_prof = self.env_resolver.resolve_node()
        git_prof = self.env_resolver.resolve_git()
        pwsh_prof = self.env_resolver.resolve_powershell()
        browser_prof = self.env_resolver.resolve_browser()

        # Test key packages in resolved Python virtualenv
        key_modules = [
            ("pymupdf", "fitz"),
            ("pypdf", "pypdf"),
            ("docx", "docx"),
            ("openpyxl", "openpyxl"),
            ("fpdf2", "fpdf"),
            ("playwright", "playwright"),
            ("pillow", "PIL"),
            ("opencv", "cv2"),
            ("chromadb", "chromadb"),
            ("psutil", "psutil"),
        ]
        package_statuses = {}
        for pkg_label, mod in key_modules:
            is_ok, ver = self.dep_resolver.verify_python_import(mod, py_prof)
            package_statuses[pkg_label] = {"available": is_ok, "version": ver}

        return {
            "platform": {
                "system": sys.platform,
                "os": os.name,
                "cwd": str(Path.cwd()),
                "project_root": self.env_resolver.default_project_root.as_posix(),
            },
            "environments": {
                "python": py_prof.to_dict(),
                "node": node_prof.to_dict(),
                "git": git_prof.to_dict(),
                "powershell": pwsh_prof.to_dict(),
                "browser": browser_prof.to_dict(),
            },
            "packages_in_python_venv": package_statuses,
            "precedence_policy": "Explicit(1) -> ProjectVenv(2) -> RepoLocal(3) -> UserEnv(4) -> SystemPath(5) -> Fallback(6)",
            "repair_policy": self.recovery_mgr.policy.value,
        }

    def start_trace(self, goal: str, task_id: Optional[str] = None) -> ExecutionTrace:
        """Create a new developer execution trace instance."""
        tid = task_id or f"trace_{uuid.uuid4().hex[:8]}"
        return ExecutionTrace(task_id=tid, goal=goal)


_GLOBAL_RUNTIME: Optional[UniversalExecutionRuntime] = None


def get_universal_runtime() -> UniversalExecutionRuntime:
    global _GLOBAL_RUNTIME
    if _GLOBAL_RUNTIME is None:
        _GLOBAL_RUNTIME = UniversalExecutionRuntime()
    return _GLOBAL_RUNTIME
