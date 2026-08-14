# multi_agent/subagent.py — BR-Jarvis Multi-Agent Sub-Agent Registry & Engine
"""
Sub-Agent Registry and Manager for BR-Jarvis.
Manages specialized multi-agent sub-delegation (Code Engineer, Security Auditor,
Data Analyst, Web Researcher, System Diagnostics) with depth limits and tool scoping.
"""
from __future__ import annotations

import logging
import queue
import uuid
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.MultiAgent")


@dataclass
class AgentDefinition:
    """Definition schema for a specialized sub-agent type."""
    name: str
    role: str
    description: str
    allowed_tools: List[str] = field(default_factory=list)
    system_prompt: str = ""
    model: str = ""
    tools: list = field(default_factory=list)
    source: str = "user"


def _parse_agent_md(path: Path, source: str = "user") -> AgentDefinition:
    """Parse a custom sub-agent markdown file."""
    content = path.read_text(encoding="utf-8")
    system_prompt_body = ""
    fm: dict = {}
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            fm_text = content[3:end].strip()
            system_prompt_body = content[end + 3:].strip()
            for line in fm_text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    fm[key.strip().lower()] = val.strip()

    name = fm.get("name", path.stem)
    role = fm.get("role", path.stem.lower())
    description = fm.get("description", "")
    tools_str = fm.get("allowed_tools", fm.get("tools", ""))
    allowed_tools = [t.strip() for t in tools_str.split(",") if t.strip()] if tools_str else []

    return AgentDefinition(
        name=name,
        role=role,
        description=description,
        allowed_tools=allowed_tools,
        system_prompt=system_prompt_body,
        model=fm.get("model", ""),
        tools=allowed_tools,
        source=source
    )


_BUILTIN_AGENTS: Dict[str, AgentDefinition] = {
    "code_engineer": AgentDefinition(
        name="Code Engineer",
        role="code_engineer",
        description="Specialized in software development, refactoring, and code debugging.",
        allowed_tools=["run_code", "file_read", "file_write", "scratchpad_write", "scratchpad_eval"],
        system_prompt="You are a senior full-stack code engineer sub-agent. Focus strictly on clean, correct code execution.",
        source="builtin",
    ),
    "security_auditor": AgentDefinition(
        name="Security Auditor",
        role="security_auditor",
        description="Specialized in security analysis, permission verification, and vulnerability audits.",
        allowed_tools=["file_read", "system_diagnostic", "nmap_scan"],
        system_prompt="You are a cybersecurity auditor sub-agent. Analyze permissions and code invariants safely.",
        source="builtin",
    ),
    "data_analyst": AgentDefinition(
        name="Data Analyst",
        role="data_analyst",
        description="Specialized in processing datasets, CSV/JSON data, and generating summaries.",
        allowed_tools=["file_read", "file_write", "run_code"],
        system_prompt="You are a data analyst sub-agent. Process raw data and produce structured summaries.",
        source="builtin",
    ),
    "web_researcher": AgentDefinition(
        name="Web Researcher",
        role="web_researcher",
        description="Specialized in retrieving online web documentation, searching information, and synthesizing reports.",
        allowed_tools=["web_search", "fetch_page"],
        system_prompt="You are a web researcher sub-agent. Gather accurate factual information from online sources.",
        source="builtin",
    ),
    "system_diagnostician": AgentDefinition(
        name="System Diagnostician",
        role="system_diagnostician",
        description="Specialized in hardware diagnostics, OS resource monitoring, and environment health checks.",
        allowed_tools=["system_diagnostic", "computer_settings", "window_manager"],
        system_prompt="You are a system diagnostic sub-agent. Inspect OS hardware, memory, and performance metrics.",
        source="builtin",
    ),
}


def load_agent_definitions() -> Dict[str, AgentDefinition]:
    """Load all agent definitions: built-ins → user-level → project-level."""
    defs: Dict[str, AgentDefinition] = dict(_BUILTIN_AGENTS)

    # User-level
    user_dir = Path.home() / ".jarvis" / "agents"
    if user_dir.is_dir():
        for p in sorted(user_dir.glob("*.md")):
            try:
                d = _parse_agent_md(p, source="user")
                defs[d.name] = d
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
    # Project-level (overrides user)
    proj_dir = Path.cwd() / ".jarvis" / "agents"
    if proj_dir.is_dir():
        for p in sorted(proj_dir.glob("*.md")):
            try:
                d = _parse_agent_md(p, source="project")
                defs[d.name] = d
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
    return defs


def get_agent_definition(name: str) -> Optional[AgentDefinition]:
    """Look up an agent definition by name. Returns None if not found."""
    return load_agent_definitions().get(name)


# ── SubAgentTask ───────────────────────────────────────────────────────────

@dataclass
class SubAgentTask:
    """Represents a sub-agent task with lifecycle tracking."""
    id: str
    prompt: str
    status: str = "pending"
    result: Optional[str] = None
    depth: int = 0
    name: str = ""
    _cancel_flag: bool = False
    _future: Optional[Future] = field(default=None, repr=False)
    _inbox: Any = field(default_factory=queue.Queue, repr=False)


# ── SubAgentManager ────────────────────────────────────────────────────────

class SubAgentManager:
    """Manages concurrent sub-agent tasks using a thread pool."""

    def __init__(self, max_concurrent: int = 5, max_depth: int = 5):
        self.tasks: Dict[str, SubAgentTask] = {}
        self._by_name: Dict[str, str] = {}
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth
        self._pool = ThreadPoolExecutor(max_workers=max_concurrent)

    def spawn(
        self,
        prompt: str,
        orchestrator,  # May be None — handled defensively below
        depth: int = 0,
        agent_def: Optional[AgentDefinition] = None,
        name: str = "",
        agent_type: str = "",   # convenience alias used by voice handler
    ) -> SubAgentTask:
        """Spawn a new sub-agent task.

        BUG-FIX: orchestrator=None is now caught immediately with a clear
        failure message rather than crashing deep inside the worker thread.
        """
        task_id = uuid.uuid4().hex[:12]
        short_name = name or task_id[:8]
        task = SubAgentTask(id=task_id, prompt=prompt, depth=depth, name=short_name)
        self.tasks[task_id] = task
        if name:
            self._by_name[name] = task_id

        # ── Guard: depth exceeded ─────────────────────────────────────────
        if depth >= self.max_depth:
            task.status = "failed"
            task.result = f"Max depth ({self.max_depth}) exceeded"
            return task

        # ── Guard: orchestrator required ──────────────────────────────────
        if orchestrator is None:
            task.status = "failed"
            task.result = (
                "Sub-agent requires an orchestrator reference. "
                "This feature is only available in the CLI (main_mk37.py) mode."
            )
            return task

        eff_system_extra = ""
        if agent_def and agent_def.system_prompt:
            eff_system_extra = agent_def.system_prompt

        def _run():
            task.status = "running"
            try:
                from memory.working import WorkingMemory
                sub_memory = WorkingMemory()

                base_system = orchestrator._build_system()
                full_system = (
                    eff_system_extra.rstrip() + "\n\n" + base_system
                    if eff_system_extra
                    else base_system
                )

                sub_memory.add("user", prompt)

                keywords = orchestrator._extract_keywords(prompt)
                profile = orchestrator.router.route(keywords)
                if profile not in orchestrator.router.backends:
                    profile = orchestrator.router.default

                from tools.registry import parse_tool_call, execute_tool
                import re

                final_response = ""
                sub_tool_counts: dict[str, int] = {}  # Sub-agent-local cyclic guard
                for _step in range(15):
                    if task._cancel_flag:
                        break


                    try:
                        response = orchestrator.router.run(
                            profile, sub_memory.get(), full_system
                        )
                    except Exception as e:
                        final_response = f"Backend error: {e}"
                        break

                    tool_name, tool_args = parse_tool_call(response)

                    if tool_name:
                        # ── Sub-agent cyclic loop guard ──
                        import json as _json
                        _sub_sig = f"{tool_name}:{_json.dumps(tool_args or {}, sort_keys=True)}"
                        sub_tool_counts[_sub_sig] = sub_tool_counts.get(_sub_sig, 0) + 1
                        _sub_limit = 4  # Sub-agents are short-lived; 4 identical calls = loop
                        if sub_tool_counts[_sub_sig] >= _sub_limit:
                            final_response = (
                                f"[SubAgent] ⛔ Cyclic-loop protection: '{tool_name}' called "
                                f"{sub_tool_counts[_sub_sig]} times inside sub-agent (limit={_sub_limit}). "
                                "Halting sub-agent to prevent token burn."
                            )
                            logger.warning("[MultiAgent] %s", final_response)
                            break

                        tool_result = execute_tool(tool_name, tool_args)
                        clean_response = re.sub(
                            r'```tool_call\s*\n\s*\{.*?\}\s*\n\s*```',
                            '', response, flags=re.DOTALL
                        ).strip()
                        if clean_response:
                            sub_memory.add("assistant", clean_response)
                        else:
                            import json
                            args_str = json.dumps(tool_args or {}, sort_keys=True)
                            sub_memory.add("assistant", f"[Executed Tool: {tool_name}({args_str})]")
                        sub_memory.add("user", f"[Tool Result for '{tool_name}']:\n{tool_result}")
                        continue
                    else:
                        final_response = response
                        break

                if task._cancel_flag:
                    task.status = "cancelled"
                    task.result = None
                else:
                    task.result = final_response
                    task.status = "completed"

                # Process inbox messages
                while not task._inbox.empty() and not task._cancel_flag:
                    inbox_msg = task._inbox.get_nowait()
                    task.status = "running"
                    sub_memory.add("user", inbox_msg)
                    try:
                        response = orchestrator.router.run(
                            profile, sub_memory.get(), full_system
                        )
                        sub_memory.add("assistant", response)
                        task.result = response
                        task.status = "completed"
                    except Exception as e:
                        task.result = f"Inbox message error: {e}"

            except Exception as e:
                task.status = "failed"
                task.result = f"Error: {e}\n{traceback.format_exc()}"

        task._future = self._pool.submit(_run)
        return task

    def spawn_subagent(
        self,
        agent_type: str,
        prompt: str,
        current_depth: int = 1,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Spawn a sub-agent task unit if depth constraints are satisfied (Compatibility API)."""
        if current_depth > self.max_depth:
            return {
                "status": "error",
                "message": f"Sub-agent depth limit ({self.max_depth}) reached. Cannot spawn deeper sub-agent."
            }

        agent_def = get_agent_definition(agent_type)
        if not agent_def:
            defs = load_agent_definitions()
            available = ", ".join(defs.keys())
            return {
                "status": "error",
                "message": f"Unknown agent type '{agent_type}'. Available types: {available}"
            }

        from tools.registry import get_orchestrator_ref
        orch = get_orchestrator_ref()

        task = self.spawn(
            prompt=prompt,
            orchestrator=orch,
            depth=current_depth,
            agent_def=agent_def,
            name=f"subagent-{agent_type}",
        )

        if task.status == "failed":
            return {
                "status": "error",
                "message": task.result or "Failed to spawn subagent"
            }

        return {
            "status": "success",
            "task_id": task.id,
            "agent_name": agent_def.name,
            "role": agent_def.role,
            "depth": current_depth,
            "allowed_tools": agent_def.allowed_tools,
            "message": f"Sub-agent '{agent_def.name}' initialized for task: '{prompt[:60]}...'"
        }

    def wait(self, task_id: str, timeout: float = None) -> Optional[SubAgentTask]:
        """Block until a task completes or timeout expires."""
        task = self.tasks.get(task_id)
        if task is None:
            return None
        if task._future is not None:
            try:
                task._future.result(timeout=timeout)
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
        return task

    def get_result(self, task_id: str) -> Optional[str]:
        """Return the result string for a completed task, or None."""
        task = self.tasks.get(task_id)
        return task.result if task else None

    def list_tasks(self) -> List[SubAgentTask]:
        """Return all tracked tasks."""
        return list(self.tasks.values())

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """Return list of active sub-agent tasks (Compatibility API)."""
        return [
            {
                "task_id": t.id,
                "agent_type": t.name,
                "status": t.status,
                "depth": t.depth,
                "prompt": t.prompt,
            }
            for t in self.tasks.values()
        ]

    def send_message(self, task_id_or_name: str, message: str) -> bool:
        """Send a message to a running background agent."""
        task_id = self._by_name.get(task_id_or_name, task_id_or_name)
        task = self.tasks.get(task_id)
        if task is None:
            return False
        if task.status not in ("running", "pending"):
            return False
        task._inbox.put(message)
        return True

    def cancel(self, task_id: str) -> bool:
        """Request cancellation of a running task."""
        task = self.tasks.get(task_id)
        if task is None:
            return False
        if task.status == "running":
            task._cancel_flag = True
            return True
        return False

    def shutdown(self) -> None:
        """Cancel all running tasks and shut down the thread pool."""
        for task in self.tasks.values():
            if task.status == "running":
                task._cancel_flag = True
        self._pool.shutdown(wait=True)
