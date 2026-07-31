# multi_agent/subagent.py — BR-Jarvis Multi-Agent Sub-Agent Registry & Engine
"""
Sub-Agent Registry and Manager for BR-Jarvis.
Manages specialized multi-agent sub-delegation (Code Engineer, Security Auditor,
Data Analyst, Web Researcher, System Diagnostics) with depth limits and tool scoping.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
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


@dataclass
class SubAgentTask:
    """Task unit assigned to a sub-agent."""
    task_id: str
    agent_type: str
    prompt: str
    depth: int = 1
    parent_id: Optional[str] = None
    status: str = "pending"
    result: Optional[str] = None


DEFAULT_AGENTS: Dict[str, AgentDefinition] = {
    "code_engineer": AgentDefinition(
        name="Code Engineer",
        role="code_engineer",
        description="Specialized in software development, refactoring, and code debugging.",
        allowed_tools=["run_code", "file_read", "file_write", "scratchpad_write", "scratchpad_eval"],
        system_prompt="You are a senior full-stack code engineer sub-agent. Focus strictly on clean, correct code execution.",
    ),
    "security_auditor": AgentDefinition(
        name="Security Auditor",
        role="security_auditor",
        description="Specialized in security analysis, permission verification, and vulnerability audits.",
        allowed_tools=["file_read", "system_diagnostic", "nmap_scan"],
        system_prompt="You are a cybersecurity auditor sub-agent. Analyze permissions and code invariants safely.",
    ),
    "data_analyst": AgentDefinition(
        name="Data Analyst",
        role="data_analyst",
        description="Specialized in processing datasets, CSV/JSON data, and generating summaries.",
        allowed_tools=["file_read", "file_write", "run_code"],
        system_prompt="You are a data analyst sub-agent. Process raw data and produce structured summaries.",
    ),
    "web_researcher": AgentDefinition(
        name="Web Researcher",
        role="web_researcher",
        description="Specialized in retrieving online web documentation, searching information, and synthesizing reports.",
        allowed_tools=["web_search", "fetch_page"],
        system_prompt="You are a web researcher sub-agent. Gather accurate factual information from online sources.",
    ),
    "system_diagnostician": AgentDefinition(
        name="System Diagnostician",
        role="system_diagnostician",
        description="Specialized in hardware diagnostics, OS resource monitoring, and environment health checks.",
        allowed_tools=["system_diagnostic", "computer_settings", "window_manager"],
        system_prompt="You are a system diagnostic sub-agent. Inspect OS hardware, memory, and performance metrics.",
    ),
}


def load_agent_definitions() -> Dict[str, AgentDefinition]:
    """Load and return all registered sub-agent definitions."""
    return dict(DEFAULT_AGENTS)


def get_agent_definition(agent_type: str) -> Optional[AgentDefinition]:
    """Retrieve a specific agent definition by name/role."""
    defs = load_agent_definitions()
    return defs.get(agent_type.lower().strip())


class SubAgentManager:
    """Manages spawning, tracking, and executing sub-agent tasks."""

    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self.active_tasks: Dict[str, SubAgentTask] = {}
        self.agent_definitions = load_agent_definitions()

    def spawn_subagent(self, agent_type: str, prompt: str, current_depth: int = 1, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Spawn a sub-agent task unit if depth constraints are satisfied."""
        if current_depth > self.max_depth:
            return {
                "status": "error",
                "message": f"Sub-agent depth limit ({self.max_depth}) reached. Cannot spawn deeper sub-agent."
            }

        agent_def = get_agent_definition(agent_type)
        if not agent_def:
            available = ", ".join(self.agent_definitions.keys())
            return {
                "status": "error",
                "message": f"Unknown agent type '{agent_type}'. Available types: {available}"
            }

        task_id = f"subagent_{uuid.uuid4().hex[:8]}"
        task = SubAgentTask(
            task_id=task_id,
            agent_type=agent_type,
            prompt=prompt,
            depth=current_depth,
            parent_id=parent_id,
            status="running"
        )
        self.active_tasks[task_id] = task

        logger.info(f"[SubAgentManager] Spawned sub-agent '{agent_def.name}' (ID: {task_id}, Depth: {current_depth})")

        return {
            "status": "success",
            "task_id": task_id,
            "agent_name": agent_def.name,
            "role": agent_def.role,
            "depth": current_depth,
            "allowed_tools": agent_def.allowed_tools,
            "message": f"Sub-agent '{agent_def.name}' initialized for task: '{prompt[:60]}...'"
        }

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """Return list of active sub-agent tasks."""
        return [
            {
                "task_id": t.task_id,
                "agent_type": t.agent_type,
                "status": t.status,
                "depth": t.depth,
                "prompt": t.prompt,
            }
            for t in self.active_tasks.values()
        ]
