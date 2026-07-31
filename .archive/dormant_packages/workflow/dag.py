# workflow/dag.py — Directed Acyclic Graph (DAG) Task Engine for JARVIS MK37
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("JARVIS.WorkflowDAG")


@dataclass
class DAGNode:
    """Represents a node in a Workflow DAG."""

    node_id: str
    name: str
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None


class WorkflowDAG:
    """DAG graph for tracking dependencies and execution order."""

    def __init__(self, workflow_id: str, name: str):
        self.workflow_id = workflow_id
        self.name = name
        self.nodes: Dict[str, DAGNode] = {}

    def add_node(self, node: DAGNode) -> None:
        """Add a node to the DAG."""
        self.nodes[node.node_id] = node

    def validate(self) -> bool:
        """Check for cycle detection in dependencies."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            node = self.nodes.get(node_id)
            if node:
                for dep in node.depends_on:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    logger.error(f"❌ Cycle detected in WorkflowDAG '{self.name}' at node '{node_id}'")
                    return False

        return True

    def get_executable_nodes(self, completed_ids: Set[str]) -> List[DAGNode]:
        """Return nodes ready for execution."""
        executable = []
        for node in self.nodes.values():
            if node.status == "pending":
                if all(dep in completed_ids for dep in node.depends_on):
                    executable.append(node)
        return executable

    def is_complete(self) -> bool:
        """Check if all nodes are in completed or failed state."""
        return all(n.status in ("completed", "failed", "skipped") for n in self.nodes.values())
