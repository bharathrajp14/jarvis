# multi_agent/__init__.py — BR-Jarvis Multi-Agent Sub-System Package
"""
Multi-Agent Orchestration & Sub-Agent Task Management Package.
"""
from multi_agent.subagent import (
    AgentDefinition,
    SubAgentTask,
    SubAgentManager,
    load_agent_definitions,
    get_agent_definition,
)

__all__ = [
    "AgentDefinition",
    "SubAgentTask",
    "SubAgentManager",
    "load_agent_definitions",
    "get_agent_definition",
]
