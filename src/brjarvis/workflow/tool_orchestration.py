# workflow/tool_orchestration.py — Multi-Tool Orchestration & Intelligent Tool Chaining Engine for BR JARVIS
"""
Production-grade multi-tool orchestration engine for BR JARVIS.
Transforms single-tool requests into capability-driven, dependency-aware execution graphs (DAGs).

Key Features:
1. ToolPlan & ToolStep data contracts with dynamic input mappings ($steps.<id>.output, $task.<field>).
2. StepResultStore with URI reference resolution (result://, artifact://, file://).
3. ToolInputMapper & DependencyResolver to pass real upstream results to downstream tools.
4. ToolHealthManager & Fallback Chains (READY, DEGRADED, DISABLED, UNAVAILABLE).
5. ParallelToolExecutor with bounded concurrency and reader-writer resource exclusion.
6. Conditional branching & bounded iteration loops with safety budgets.
7. Atomic SQLite WAL Checkpointing & Crash Resume.
8. Multi-Stage Action & Workflow Verification (SUCCESS_VERIFIED, PARTIAL_SUCCESS, FAILED).
9. Memory & Lessons extraction for successful multi-tool workflow topologies.
"""
from __future__ import annotations

import concurrent.futures
import copy
import json
import logging
import os
import re
import sqlite3
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

logger = logging.getLogger("JARVIS.ToolOrchestrator")


# ── 1. Enums and Data Models ──────────────────────────────────────────────────

class ToolHealthStatus(str, Enum):
    READY       = "READY"
    DEGRADED    = "DEGRADED"
    DISABLED    = "DISABLED"
    BLOCKED     = "BLOCKED"
    UNAVAILABLE = "UNAVAILABLE"


class StepExecutionStatus(str, Enum):
    PENDING              = "PENDING"
    READY                = "READY"
    RUNNING              = "RUNNING"
    SUCCESS_VERIFIED     = "SUCCESS_VERIFIED"
    SUCCESS_UNVERIFIED   = "SUCCESS_UNVERIFIED"
    PARTIAL_SUCCESS      = "PARTIAL_SUCCESS"
    FAILED               = "FAILED"
    CANCELLED            = "CANCELLED"
    SKIPPED              = "SKIPPED"
    WAITING_APPROVAL     = "WAITING_APPROVAL"


class TaskExecutionStatus(str, Enum):
    CREATED          = "CREATED"
    RUNNING          = "RUNNING"
    SUCCESS_VERIFIED = "SUCCESS_VERIFIED"
    PARTIAL_SUCCESS  = "PARTIAL_SUCCESS"
    FAILED           = "FAILED"
    CANCELLED        = "CANCELLED"


class ToolCategory(str, Enum):
    WEB_SEARCH     = "WEB_SEARCH"
    FILE_SYSTEM    = "FILE_SYSTEM"
    REPO_ANALYSIS  = "REPO_ANALYSIS"
    BROWSER        = "BROWSER"
    OFFICE_DOC     = "OFFICE_DOC"
    SYSTEM_DIAG    = "SYSTEM_DIAG"
    CODE_EXEC      = "CODE_EXEC"
    COMMUNICATION  = "COMMUNICATION"
    MEMORY         = "MEMORY"
    GENERAL        = "GENERAL"


@dataclass
class ToolDependency:
    step_id: str
    required_field: Optional[str] = None
    is_optional: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolDependency:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ToolStep:
    step_id: str
    tool: str
    title: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_mappings: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    fallback_tools: List[str] = field(default_factory=list)
    category: ToolCategory = ToolCategory.GENERAL
    is_write: bool = False
    resource_keys: List[str] = field(default_factory=list)
    is_critical: bool = True
    condition: Optional[str] = None
    timeout_sec: float = 30.0
    max_retries: int = 1
    requires_approval: bool = False
    status: StepExecutionStatus = StepExecutionStatus.PENDING
    result: Any = None
    evidence: str = ""
    error: Optional[str] = None
    executed_at: Optional[float] = None
    duration_sec: float = 0.0
    fallback_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value if isinstance(self.category, ToolCategory) else str(self.category)
        d["status"] = self.status.value if isinstance(self.status, StepExecutionStatus) else str(self.status)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolStep:
        raw = dict(data)
        if "category" in raw and isinstance(raw["category"], str):
            try:
                raw["category"] = ToolCategory(raw["category"])
            except ValueError:
                raw["category"] = ToolCategory.GENERAL
        if "status" in raw and isinstance(raw["status"], str):
            try:
                raw["status"] = StepExecutionStatus(raw["status"])
            except ValueError:
                raw["status"] = StepExecutionStatus.PENDING
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


@dataclass
class ToolPlan:
    task_id: str
    goal: str
    steps: List[ToolStep] = field(default_factory=list)
    status: TaskExecutionStatus = TaskExecutionStatus.CREATED
    completion_predicate: Optional[str] = None
    max_concurrency: int = 4
    max_iterations: int = 10
    timeout_sec: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, TaskExecutionStatus) else str(self.status)
        d["steps"] = [s.to_dict() if isinstance(s, ToolStep) else s for s in self.steps]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolPlan:
        raw = dict(data)
        if "status" in raw and isinstance(raw["status"], str):
            try:
                raw["status"] = TaskExecutionStatus(raw["status"])
            except ValueError:
                raw["status"] = TaskExecutionStatus.CREATED
        if "steps" in raw and isinstance(raw["steps"], list):
            raw["steps"] = [ToolStep.from_dict(s) if isinstance(s, dict) else s for s in raw["steps"]]
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


# ── 2. Step Result & Reference Store ──────────────────────────────────────────

class StepResultStore:
    """
    Centralized store for structured tool outputs, artifact references, and telemetry.
    Supports reference resolution:
      result://<task_id>/<step_id>[/<key>]
      artifact://<task_id>/<filename>
      file://<path>
    """

    def __init__(self):
        self._results: Dict[str, Dict[str, Any]] = {}
        self._artifacts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def store_result(self, task_id: str, step_id: str, result_data: Any, evidence: str = "") -> None:
        with self._lock:
            if task_id not in self._results:
                self._results[task_id] = {}
            self._results[task_id][step_id] = {
                "data": result_data,
                "evidence": evidence,
                "timestamp": time.time(),
            }

    def get_result(self, task_id: str, step_id: str) -> Optional[Any]:
        with self._lock:
            task_res = self._results.get(task_id, {})
            step_record = task_res.get(step_id)
            if step_record:
                return step_record.get("data")
            return None

    def store_artifact(self, task_id: str, name: str, path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            if task_id not in self._artifacts:
                self._artifacts[task_id] = {}
            self._artifacts[task_id][name] = {
                "path": str(Path(path).resolve()),
                "metadata": metadata or {},
                "timestamp": time.time(),
            }

    def get_artifact(self, task_id: str, name: str) -> Optional[str]:
        with self._lock:
            return self._artifacts.get(task_id, {}).get(name, {}).get("path")

    def resolve_reference(self, task_id: str, ref: str) -> Any:
        """Resolve URI references such as result://, artifact://, and file://."""
        if not isinstance(ref, str):
            return ref

        ref_clean = ref.strip()

        # 1. result://task_id/step_id or result://step_id or result://step_id/path.to.key
        if ref_clean.startswith("result://"):
            parts = ref_clean[9:].split("/")
            if len(parts) == 1:
                target_tid, step_id = task_id, parts[0]
                key_path = None
            elif len(parts) == 2:
                # If first part is a known step in this task, treat as step/key, else tid/step
                if task_id in self._results and parts[0] in self._results[task_id]:
                    target_tid, step_id = task_id, parts[0]
                    key_path = parts[1]
                else:
                    target_tid, step_id = parts[0], parts[1]
                    key_path = None
            else:
                target_tid = parts[0]
                step_id = parts[1]
                key_path = ".".join(parts[2:])

            raw_res = self.get_result(target_tid, step_id)
            if key_path and isinstance(raw_res, dict):
                return self._extract_by_key_path(raw_res, key_path)
            return raw_res

        # 2. artifact://task_id/name or artifact://name
        if ref_clean.startswith("artifact://"):
            parts = ref_clean[11:].split("/")
            if len(parts) == 1:
                target_tid, name = task_id, parts[0]
            else:
                target_tid, name = parts[0], parts[1]
            return self.get_artifact(target_tid, name) or ref_clean

        # 3. file://path
        if ref_clean.startswith("file://"):
            clean_path = ref_clean[7:]
            if sys.platform == "win32" and clean_path.startswith("/"):
                clean_path = clean_path[1:]
            return clean_path

        return ref

    @staticmethod
    def _extract_by_key_path(data: Any, key_path: str) -> Any:
        curr = data
        for part in key_path.split("."):
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            elif isinstance(curr, list) and part.isdigit() and int(part) < len(curr):
                curr = curr[int(part)]
            else:
                return None
        return curr


_global_result_store: Optional[StepResultStore] = None


def get_step_result_store() -> StepResultStore:
    global _global_result_store
    if _global_result_store is None:
        _global_result_store = StepResultStore()
    return _global_result_store


# ── 3. Tool Input Mapper & Dependency Resolver ────────────────────────────────

class ToolInputMapper:
    """
    Dynamically maps parameters for a step using upstream execution outputs,
    result store URIs, and user task context without hallucination.
    """

    @classmethod
    def resolve_inputs(
        cls,
        step: ToolStep,
        task: ToolPlan,
        result_store: Optional[StepResultStore] = None,
        step_outputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        store = result_store or get_step_result_store()
        outputs = step_outputs or {}
        resolved = dict(step.parameters)

        # Process declared input mappings: e.g. {"query": "$task.user_query", "path": "$steps.create_doc.output.path"}
        for param_name, expr in step.input_mappings.items():
            if not isinstance(expr, str):
                resolved[param_name] = expr
                continue

            val = cls._evaluate_expression(expr, task, outputs, store)
            if val is not None:
                resolved[param_name] = val

        # Also scan string values in parameters for inline placeholders or URI schemes
        for k, v in list(resolved.items()):
            if isinstance(v, str):
                if v.startswith(("result://", "artifact://", "file://")):
                    resolved[k] = store.resolve_reference(task.task_id, v)
                elif v.startswith("$"):
                    val = cls._evaluate_expression(v, task, outputs, store)
                    if val is not None:
                        resolved[k] = val

        return resolved

    @classmethod
    def _evaluate_expression(
        cls,
        expr: str,
        task: ToolPlan,
        outputs: Dict[str, Any],
        store: StepResultStore,
    ) -> Any:
        expr = expr.strip()

        # 1. $task.<field>
        if expr.startswith("$task."):
            attr = expr[6:]
            if attr in ("goal", "user_query", "query", "prompt"):
                return task.goal
            if hasattr(task, attr):
                return getattr(task, attr)
            if attr in task.metadata:
                return task.metadata[attr]
            return None

        # 2. $steps.<step_id>.<path>
        if expr.startswith("$steps."):
            parts = expr[7:].split(".")
            step_id = parts[0]
            sub_path = ".".join(parts[1:]) if len(parts) > 1 else ""

            # Fetch step output from local outputs dict or result store
            step_out = outputs.get(step_id)
            if step_out is None:
                step_out = store.get_result(task.task_id, step_id)

            if step_out is None:
                return None

            if not sub_path or sub_path in ("output", "result", "data"):
                return step_out

            if sub_path.startswith("output."):
                sub_path = sub_path[7:]
            elif sub_path.startswith("result."):
                sub_path = sub_path[7:]
            elif sub_path.startswith("data."):
                sub_path = sub_path[5:]

            if isinstance(step_out, dict):
                return store._extract_by_key_path(step_out, sub_path)
            elif hasattr(step_out, sub_path):
                return getattr(step_out, sub_path)

            return step_out

        # 3. $artifacts.<name>
        if expr.startswith("$artifacts."):
            name = expr[11:]
            return store.get_artifact(task.task_id, name)

        # 4. Fallback to URI resolution
        if expr.startswith(("result://", "artifact://", "file://")):
            return store.resolve_reference(task.task_id, expr)

        return None


# ── 4. Tool Health & Fallback Manager ─────────────────────────────────────────

class ToolHealthManager:
    """
    Maintains health status and prioritized fallback tool chains across tool categories.
    Ensures graceful degradation when primary tools fail or require unavailable permissions.
    """

    def __init__(self):
        self._health: Dict[str, ToolHealthStatus] = {}
        self._category_tools: Dict[ToolCategory, List[str]] = {
            ToolCategory.WEB_SEARCH: [
                "web_search", "fetch_page", "browser_control"
            ],
            ToolCategory.OFFICE_DOC: [
                "document_creator", "create_word_document", "create_pdf_document"
            ],
            ToolCategory.BROWSER: [
                "browser_control", "open_app", "browser_open_url"
            ],
            ToolCategory.FILE_SYSTEM: [
                "file_controller", "file_read", "file_write"
            ],
            ToolCategory.REPO_ANALYSIS: [
                "file_read", "git_repo_mgr", "code_helper"
            ],
            ToolCategory.SYSTEM_DIAG: [
                "system_diagnostic", "system_monitor", "computer_settings"
            ],
            ToolCategory.CODE_EXEC: [
                "code_helper", "dev_agent", "scratchpad_eval"
            ],
            ToolCategory.COMMUNICATION: [
                "send_message", "smart_email_sender", "email_assistant"
            ],
        }
        self._fallback_records: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def set_health(self, tool_name: str, status: ToolHealthStatus) -> None:
        with self._lock:
            self._health[tool_name] = status
            logger.info("[ToolHealth] Tool '%s' status updated to %s", tool_name, status.value)

    def get_health(self, tool_name: str) -> ToolHealthStatus:
        with self._lock:
            return self._health.get(tool_name, ToolHealthStatus.READY)

    def is_available(self, tool_name: str) -> bool:
        status = self.get_health(tool_name)
        return status in (ToolHealthStatus.READY, ToolHealthStatus.DEGRADED)

    def get_fallback_chain(self, tool_name: str, category: Optional[ToolCategory] = None) -> List[str]:
        """Return compatible fallback tools for a given tool name."""
        fallbacks: List[str] = []
        cat = category

        # Identify category if not provided
        if not cat:
            for c, tools in self._category_tools.items():
                if tool_name in tools:
                    cat = c
                    break

        if cat and cat in self._category_tools:
            fallbacks = [t for t in self._category_tools[cat] if t != tool_name]

        return fallbacks

    def record_fallback(self, primary: str, fallback: str, reason: str, success: bool) -> None:
        with self._lock:
            rec = {
                "primary_failed": primary,
                "fallback_selected": fallback,
                "fallback_reason": reason,
                "fallback_success": success,
                "timestamp": time.time(),
            }
            self._fallback_records.append(rec)
            logger.warning(
                "🔄 [ToolFallback] Primary '%s' failed (%s) -> Selected fallback '%s' (Success: %s)",
                primary, reason, fallback, success
            )


_global_health_manager: Optional[ToolHealthManager] = None


def get_tool_health_manager() -> ToolHealthManager:
    global _global_health_manager
    if _global_health_manager is None:
        _global_health_manager = ToolHealthManager()
    return _global_health_manager


# ── 5. Graph Topology & Cycle Detection ───────────────────────────────────────

class ExecutionGraph:
    """
    Directed Acyclic Graph (DAG) for multi-tool execution with dependency resolution,
    cycle detection, topological wave generation, and resource exclusion.
    """

    def __init__(self, plan: ToolPlan):
        self.plan = plan
        self.steps = plan.steps
        self.step_map: Dict[str, ToolStep] = {s.step_id: s for s in self.steps}
        self.validate_graph()

    def validate_graph(self) -> None:
        """Validate DAG: check that all dependencies exist and no cycles are present."""
        all_ids = set(self.step_map.keys())
        in_degree: Dict[str, int] = {sid: 0 for sid in all_ids}
        adj: Dict[str, List[str]] = {sid: [] for sid in all_ids}

        for step in self.steps:
            for dep in step.dependencies:
                if dep not in all_ids:
                    logger.warning("[ExecutionGraph] Dependency '%s' not found in step '%s'", dep, step.step_id)
                    continue
                adj[dep].append(step.step_id)
                in_degree[step.step_id] += 1

        # Kahn's BFS cycle check
        queue = deque(sid for sid, deg in in_degree.items() if deg == 0)
        processed = 0

        while queue:
            curr = queue.popleft()
            processed += 1
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if processed < len(all_ids):
            cycle_nodes = [sid for sid, deg in in_degree.items() if deg > 0]
            raise ValueError(f"[ExecutionGraph] Cycle detected in task '{self.plan.task_id}'! Cycle nodes: {cycle_nodes}")

    def get_ready_steps(self, completed_ids: Set[str], failed_ids: Set[str]) -> List[ToolStep]:
        """Find pending steps whose non-optional dependencies and condition prerequisites are met."""
        ready: List[ToolStep] = []
        for step in self.steps:
            if step.status != StepExecutionStatus.PENDING:
                continue

            # If step condition references other steps ($steps.<id>), ensure those steps have completed or failed
            cond_steps = re.findall(r"\$steps\.([\w\-]+)", step.condition or "")
            if cond_steps and not all(cs in completed_ids or cs in failed_ids for cs in cond_steps):
                continue

            # Check if this step is a designated failure handler for any upstream failures
            has_failure_handler = bool(step.condition and ("FAILED" in step.condition or "!=" in step.condition))

            # If any required dependency failed:
            if any(dep in failed_ids for dep in step.dependencies):
                if not has_failure_handler:
                    step.status = StepExecutionStatus.SKIPPED
                    step.error = "Upstream dependency failed"
                    continue

            # Check if all dependencies are completed (or accounted for by failure handler)
            if all(dep in completed_ids or (dep in failed_ids and has_failure_handler) for dep in step.dependencies):
                ready.append(step)

        return ready


    def form_conflict_free_wave(self, candidate_steps: List[ToolStep], max_wave_size: int) -> List[ToolStep]:
        """Form a wave of steps respecting Reader-Writer exclusion locks on resource keys."""
        wave: List[ToolStep] = []
        wave_write_keys: Set[str] = set()
        wave_read_keys: Set[str] = set()

        for step in candidate_steps:
            if len(wave) >= max_wave_size:
                break

            r_keys = set(step.resource_keys or [])
            if step.is_write:
                # Writer cannot share keys with any active readers or writers
                if r_keys.intersection(wave_write_keys) or r_keys.intersection(wave_read_keys):
                    continue
                wave.append(step)
                wave_write_keys.update(r_keys)
            else:
                # Reader cannot share keys with active writers
                if r_keys.intersection(wave_write_keys):
                    continue
                wave.append(step)
                wave_read_keys.update(r_keys)

        return wave


# ── 6. Persistent Task Checkpointer (SQLite WAL) ──────────────────────────────

class TaskCheckpointer:
    """
    Atomic SQLite WAL storage engine for persisting multi-tool plans,
    execution progress, verified outputs, and resume state.
    """

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            try:
                from brjarvis.memory.persistent_store import get_memory_dir
            except ImportError:
                from brjarvis.memory.persistent_store import get_memory_dir
            db_dir = get_memory_dir("user")
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / "tool_orchestration.db"
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_plans (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_plan_steps (
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_data TEXT,
                    evidence TEXT,
                    error TEXT,
                    duration_sec REAL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (task_id, step_id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def checkpoint_plan(self, plan: ToolPlan) -> None:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            plan.updated_at = time.time()
            plan_json = json.dumps(plan.to_dict(), ensure_ascii=False)
            conn.execute(
                "INSERT OR REPLACE INTO tool_plans (task_id, goal, status, plan_data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (plan.task_id, plan.goal, plan.status.value, plan_json, plan.created_at, plan.updated_at)
            )

            for step in plan.steps:
                res_str = json.dumps(step.result, ensure_ascii=False) if step.result is not None else None
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tool_plan_steps
                    (task_id, step_id, tool, status, result_data, evidence, error, duration_sec, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.task_id, step.step_id, step.tool,
                        step.status.value if isinstance(step.status, StepExecutionStatus) else str(step.status),
                        res_str, step.evidence, step.error, step.duration_sec, time.time()
                    )
                )
            conn.commit()
        finally:
            conn.close()

    def load_plan(self, task_id: str) -> Optional[ToolPlan]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT plan_data FROM tool_plans WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None

            plan_dict = json.loads(row["plan_data"])
            return ToolPlan.from_dict(plan_dict)
        finally:
            conn.close()


_global_checkpointer: Optional[TaskCheckpointer] = None


def get_task_checkpointer() -> TaskCheckpointer:
    global _global_checkpointer
    if _global_checkpointer is None:
        _global_checkpointer = TaskCheckpointer()
    return _global_checkpointer


# ── 7. Conditional Branching & Evaluation ─────────────────────────────────────

class ConditionalEvaluator:
    """Evaluates predicate conditions for dynamic branching and supplemental execution."""

    @staticmethod
    def evaluate(condition_str: Optional[str], context: Dict[str, Any]) -> bool:
        if not condition_str:
            return True

        cond = condition_str.strip()

        # Direct boolean values
        if cond.lower() == "true":
            return True
        if cond.lower() == "false":
            return False

        # Pattern: $steps.<step_id>.status == '<STATUS>'
        m_status = re.match(r"^\$steps\.([\w\-]+)\.status\s*==\s*['\"]([\w\-]+)['\"]$", cond)
        if m_status:
            step_id, expected = m_status.groups()
            step_obj = context.get(step_id, {})
            actual_status = step_obj.get("status") if isinstance(step_obj, dict) else getattr(step_obj, "status", None)
            if hasattr(actual_status, "value"):
                actual_status = actual_status.value
            return str(actual_status).upper() == expected.upper()

        # Pattern: $steps.<step_id>.status != '<STATUS>'
        m_status_neq = re.match(r"^\$steps\.([\w\-]+)\.status\s*!=\s*['\"]([\w\-]+)['\"]$", cond)
        if m_status_neq:
            step_id, expected = m_status_neq.groups()
            step_obj = context.get(step_id, {})
            actual_status = step_obj.get("status") if isinstance(step_obj, dict) else getattr(step_obj, "status", None)
            if hasattr(actual_status, "value"):
                actual_status = actual_status.value
            return str(actual_status).upper() != expected.upper()

        # Pattern: $steps.<step_id>.output.<key> exists / is not empty
        m_key = re.match(r"^\$steps\.([\w\-]+)\.output\.([\w\.\-]+)$", cond)
        if m_key:
            step_id, key_name = m_key.groups()
            step_out = context.get(step_id, {}).get("output") if isinstance(context.get(step_id), dict) else None
            if isinstance(step_out, dict):
                return bool(step_out.get(key_name))
            return False

        return True


# ── 8. Parallel Multi-Tool Execution Engine ───────────────────────────────────

@dataclass
class WorkflowExecutionReport:
    task_id: str
    goal: str
    status: TaskExecutionStatus
    completed_steps: List[str]
    failed_steps: List[str]
    partial_steps: List[str]
    results: Dict[str, Any]
    evidence_records: List[str]
    duration_sec: float
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status.value,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "partial_steps": self.partial_steps,
            "results": self.results,
            "evidence_records": self.evidence_records,
            "duration_sec": self.duration_sec,
            "summary": self.summary,
        }


class ParallelToolExecutor:
    """
    Core dependency-aware parallel executor for multi-tool plans.
    Runs independent tools concurrently, maps dynamic parameters, enforces fallback chains,
    verifies actions independently, and performs SQLite WAL checkpoints.
    """

    def __init__(
        self,
        tool_runner: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        checkpointer: Optional[TaskCheckpointer] = None,
        result_store: Optional[StepResultStore] = None,
        health_manager: Optional[ToolHealthManager] = None,
        max_concurrency: int = 4,
    ):
        self.tool_runner = tool_runner or self._default_tool_runner
        self.checkpointer = checkpointer or get_task_checkpointer()
        self.result_store = result_store or get_step_result_store()
        self.health_manager = health_manager or get_tool_health_manager()
        self.max_concurrency = max_concurrency

    @staticmethod
    def _default_tool_runner(tool_name: str, args: Dict[str, Any]) -> Any:
        try:
            from brjarvis.tools.registry import execute_tool
        except ImportError:
            from brjarvis.tools.registry import execute_tool
        return execute_tool(tool_name, args)

    def execute_plan(
        self,
        plan: ToolPlan,
        cancel_event: Optional[threading.Event] = None,
        progress_callback: Optional[Callable[[ToolStep, int, int], None]] = None,
    ) -> WorkflowExecutionReport:
        t_start = time.monotonic()
        graph = ExecutionGraph(plan)
        plan.status = TaskExecutionStatus.RUNNING
        self.checkpointer.checkpoint_plan(plan)

        completed_ids: Set[str] = set()
        failed_ids: Set[str] = set()
        partial_ids: Set[str] = set()
        step_outputs: Dict[str, Any] = {}
        evidence_records: List[str] = []

        # Pre-populate completed/failed steps from previous checkpoint if resuming
        for step in plan.steps:
            if step.status == StepExecutionStatus.SUCCESS_VERIFIED:
                completed_ids.add(step.step_id)
                if step.result is not None:
                    step_outputs[step.step_id] = step.result
                if step.evidence:
                    evidence_records.append(f"[{step.tool}] {step.evidence}")
            elif step.status == StepExecutionStatus.PARTIAL_SUCCESS:
                completed_ids.add(step.step_id)
                partial_ids.add(step.step_id)
                if step.result is not None:
                    step_outputs[step.step_id] = step.result
            elif step.status in (StepExecutionStatus.FAILED, StepExecutionStatus.SKIPPED, StepExecutionStatus.CANCELLED):
                failed_ids.add(step.step_id)

        total_steps_count = len(plan.steps)
        logger.info("🚀 [ParallelToolExecutor] Starting execution for task '%s' (%d steps, %d already completed)", plan.task_id, total_steps_count, len(completed_ids))


        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_concurrency, plan.max_concurrency)) as pool:
            while len(completed_ids) + len(failed_ids) < total_steps_count:
                if cancel_event and cancel_event.is_set():
                    logger.warning("[ParallelToolExecutor] Task '%s' cancelled by user signal", plan.task_id)
                    plan.status = TaskExecutionStatus.CANCELLED
                    self.checkpointer.checkpoint_plan(plan)
                    return WorkflowExecutionReport(
                        task_id=plan.task_id,
                        goal=plan.goal,
                        status=TaskExecutionStatus.CANCELLED,
                        completed_steps=list(completed_ids),
                        failed_steps=list(failed_ids),
                        partial_steps=list(partial_ids),
                        results=step_outputs,
                        evidence_records=evidence_records,
                        duration_sec=time.monotonic() - t_start,
                        summary="Task was cancelled by user.",
                    )

                # 1. Retrieve all candidate steps whose dependencies have succeeded
                candidate_steps = graph.get_ready_steps(completed_ids, failed_ids)
                if not candidate_steps:
                    # No ready steps — check if remaining steps are skipped/blocked
                    remaining = [s for s in plan.steps if s.status == StepExecutionStatus.PENDING]
                    if remaining:
                        for s in remaining:
                            s.status = StepExecutionStatus.SKIPPED
                            s.error = "Unresolved or failed dependencies"
                            failed_ids.add(s.step_id)
                    break

                # 2. Filter by conditional branching expressions
                valid_candidates: List[ToolStep] = []
                for step in candidate_steps:
                    eval_ctx = {
                        sid: {"status": s.status, "output": step_outputs.get(sid), "evidence": s.evidence}
                        for sid, s in graph.step_map.items()
                    }
                    if not ConditionalEvaluator.evaluate(step.condition, eval_ctx):
                        logger.info("[ParallelToolExecutor] Step '%s' condition '%s' evaluated to False -> Skipping", step.step_id, step.condition)
                        step.status = StepExecutionStatus.SKIPPED
                        step.result = "Condition evaluated to False"
                        completed_ids.add(step.step_id)
                        continue
                    valid_candidates.append(step)

                if not valid_candidates:
                    continue

                # 3. Form a conflict-free execution wave (respecting resource keys & concurrency)
                wave = graph.form_conflict_free_wave(valid_candidates, max_wave_size=self.max_concurrency)

                # 4. Resolve dynamic inputs for all steps in this wave
                for step in wave:
                    step.status = StepExecutionStatus.RUNNING
                    step.executed_at = time.time()
                    step.parameters = ToolInputMapper.resolve_inputs(step, plan, self.result_store, step_outputs)

                # 5. Dispatch wave to ThreadPoolExecutor
                futures = {
                    pool.submit(self._execute_single_step, step, plan): step
                    for step in wave
                }

                for future in concurrent.futures.as_completed(futures):
                    step = futures[future]
                    step_duration = time.time() - (step.executed_at or time.time())
                    step.duration_sec = step_duration

                    try:
                        step_res, v_status, evidence = future.result()
                        step.result = step_res
                        step.evidence = evidence
                        step.status = v_status
                        step_outputs[step.step_id] = step_res
                        self.result_store.store_result(plan.task_id, step.step_id, step_res, evidence)

                        if evidence:
                            evidence_records.append(f"[{step.tool}] {evidence}")

                        if v_status == StepExecutionStatus.SUCCESS_VERIFIED:
                            completed_ids.add(step.step_id)
                        elif v_status == StepExecutionStatus.PARTIAL_SUCCESS:
                            completed_ids.add(step.step_id)
                            partial_ids.add(step.step_id)
                        else:
                            failed_ids.add(step.step_id)

                    except Exception as exc:
                        logger.error("[ParallelToolExecutor] Step '%s' uncaught error: %s", step.step_id, exc)
                        step.status = StepExecutionStatus.FAILED
                        step.error = str(exc)
                        failed_ids.add(step.step_id)

                    if progress_callback:
                        progress_callback(step, len(completed_ids) + len(failed_ids), total_steps_count)

                # Checkpoint after each wave
                self.checkpointer.checkpoint_plan(plan)

        # 6. Overall Workflow Status Determination with TaskCompletionGate
        duration = time.monotonic() - t_start
        try:
            from brjarvis.core.execution.completion_gate import get_task_completion_gate
            from brjarvis.core.execution.types import ExecutionStatus
            
            step_dicts = [s.to_dict() for s in plan.steps]
            gate_res = get_task_completion_gate().evaluate_task(plan.goal, step_dicts, step_outputs)
            
            if gate_res.final_status == ExecutionStatus.SUCCESS_VERIFIED:
                plan.status = TaskExecutionStatus.SUCCESS_VERIFIED
            elif gate_res.final_status == ExecutionStatus.PARTIAL_SUCCESS:
                plan.status = TaskExecutionStatus.PARTIAL_SUCCESS
            else:
                plan.status = TaskExecutionStatus.FAILED
        except Exception:
            critical_failed = any(
                s.status == StepExecutionStatus.FAILED and s.is_critical
                for s in plan.steps
            )
            if not critical_failed and len(failed_ids) == 0:
                plan.status = TaskExecutionStatus.SUCCESS_VERIFIED
            elif len(completed_ids) > 0:
                plan.status = TaskExecutionStatus.PARTIAL_SUCCESS
            else:
                plan.status = TaskExecutionStatus.FAILED

        self.checkpointer.checkpoint_plan(plan)

        # 7. Learn successful workflows into memory
        if plan.status in (TaskExecutionStatus.SUCCESS_VERIFIED, TaskExecutionStatus.PARTIAL_SUCCESS):
            self._save_workflow_learning(plan)

        # Format evidence summary
        summary = self._synthesize_execution_summary(plan, evidence_records)

        return WorkflowExecutionReport(
            task_id=plan.task_id,
            goal=plan.goal,
            status=plan.status,
            completed_steps=list(completed_ids),
            failed_steps=list(failed_ids),
            partial_steps=list(partial_ids),
            results=step_outputs,
            evidence_records=evidence_records,
            duration_sec=duration,
            summary=summary,
        )

    def _execute_single_step(self, step: ToolStep, plan: ToolPlan) -> Tuple[Any, StepExecutionStatus, str]:
        """Execute a single step with retries, fallback tool switching, and ActionVerifier verification."""
        from brjarvis.agent.verifier import get_action_verifier, VerificationStatus
        verifier = get_action_verifier()

        active_tool = step.tool
        fallback_candidates = list(step.fallback_tools) or self.health_manager.get_fallback_chain(step.tool, step.category)
        all_attempts = [active_tool] + fallback_candidates

        last_error = None
        for candidate_tool in all_attempts:
            # Skip disabled/blocked tools
            if not self.health_manager.is_available(candidate_tool):
                logger.warning("[StepExec] Skipping tool '%s' (Health: %s)", candidate_tool, self.health_manager.get_health(candidate_tool))
                continue

            for attempt in range(step.max_retries + 1):
                try:
                    logger.info("▶ [StepExec] Step '%s' invoking tool '%s' (Attempt %d)", step.step_id, candidate_tool, attempt + 1)
                    raw_result = self.tool_runner(candidate_tool, step.parameters)

                    # Verify tool execution outcome
                    v_res = verifier.verify_action(candidate_tool, step.parameters, str(raw_result))

                    if v_res.verified and v_res.status == VerificationStatus.SUCCESS_VERIFIED:
                        if candidate_tool != step.tool:
                            step.fallback_used = candidate_tool
                            self.health_manager.record_fallback(step.tool, candidate_tool, str(last_error or "primary failed"), True)
                        return raw_result, StepExecutionStatus.SUCCESS_VERIFIED, v_res.evidence or v_res.details
                    elif v_res.status == VerificationStatus.PARTIAL_SUCCESS:
                        return raw_result, StepExecutionStatus.PARTIAL_SUCCESS, v_res.evidence or v_res.details
                    else:
                        last_error = v_res.error or v_res.details or "Verification failed"
                        logger.warning("[StepExec] Step '%s' tool '%s' verification rejected: %s", step.step_id, candidate_tool, last_error)

                except Exception as err:
                    last_error = err
                    logger.warning("[StepExec] Step '%s' tool '%s' exception: %s", step.step_id, candidate_tool, err)

        # All tool attempts exhausted
        return None, StepExecutionStatus.FAILED, f"All attempts failed. Last error: {last_error}"

    def _synthesize_execution_summary(self, plan: ToolPlan, evidence_records: List[str]) -> str:
        lines = [
            f"### Multi-Tool Execution Report for Task: {plan.goal}",
            f"**Status**: {plan.status.value}",
            "",
            "#### Step Execution Details:"
        ]
        for idx, step in enumerate(plan.steps, start=1):
            icon = "✅" if step.status == StepExecutionStatus.SUCCESS_VERIFIED else "⚠️" if step.status == StepExecutionStatus.PARTIAL_SUCCESS else "❌" if step.status == StepExecutionStatus.FAILED else "⏭️"
            fallback_note = f" (fallback: {step.fallback_used})" if step.fallback_used else ""
            lines.append(f"{idx}. {icon} **{step.title or step.tool}** (`{step.tool}`{fallback_note}): {step.status.value}")
            if step.evidence:
                lines.append(f"   - Evidence: {step.evidence}")
            if step.error:
                lines.append(f"   - Error: {step.error}")

        return "\n".join(lines)

    def _save_workflow_learning(self, plan: ToolPlan) -> None:
        """Record successful workflow sequence and tool substitutions to memory and lessons store."""
        try:
            tools_used = [s.tool for s in plan.steps if s.status in (StepExecutionStatus.SUCCESS_VERIFIED, StepExecutionStatus.PARTIAL_SUCCESS)]
            seq_desc = " -> ".join(tools_used)

            # 1. Record in LessonStore
            try:
                from brjarvis.memory.lessons import LessonStore
                ls = LessonStore()
                ls.record_workflow_lesson(workflow_name=plan.goal[:40], sequence_desc=seq_desc, success=True)
            except Exception as ls_err:
                logger.debug("[ParallelToolExecutor] LessonStore note: %s", ls_err)

            # 2. Record in UnifiedMemory
            from brjarvis.memory.unified_memory import get_unified_memory
            um = get_unified_memory()
            content = f"Workflow sequence for '{plan.goal}': {seq_desc}"
            um.save(category="operational", name=f"workflow_{plan.task_id[:8]}", content=content, importance=0.8)
        except Exception as exc:
            logger.debug("[ParallelToolExecutor] Learning record skipped: %s", exc)



_global_parallel_executor: Optional[ParallelToolExecutor] = None


def get_parallel_tool_executor() -> ParallelToolExecutor:
    global _global_parallel_executor
    if _global_parallel_executor is None:
        _global_parallel_executor = ParallelToolExecutor()
    return _global_parallel_executor
