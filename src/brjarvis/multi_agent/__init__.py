# multi_agent/__init__.py — BR-Jarvis Multi-Agent Sub-System Package
"""
Multi-Agent Orchestration & Sub-Agent Task Management Package.
"""

from .subagent import (
    AgentDefinition,
    SubAgentManager,
    SubAgentTask,
    get_agent_definition,
    load_agent_definitions,
)

__all__ = [
    "AgentDefinition",
    "SubAgentTask",
    "SubAgentManager",
    "load_agent_definitions",
    "get_agent_definition",
]
