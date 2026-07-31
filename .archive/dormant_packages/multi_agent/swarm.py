# multi_agent/swarm.py — Hierarchical Multi-Agent Swarm Collaboration Engine
"""
Hierarchical Swarm Collaboration establishing role specialization:
Architect -> Domain Specialists (Coder, DevOps, Security) -> Critic Reviewer -> Integrator.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS.MultiAgentSwarm")


class SwarmAgentRole(BaseModel):
    """Definition of an individual agent role in the swarm."""

    name: str
    role_type: str  # ARCHITECT, SPECIALIST, CRITIC, INTEGRATOR
    instructions: str
    capabilities: List[str] = Field(default_factory=list)


class SwarmTaskAssignment(BaseModel):
    """Sub-task assignment dispatched to a swarm agent."""

    task_id: str
    assigned_role: str
    sub_goal: str
    output: Optional[str] = None
    approved_by_critic: bool = False


class MultiAgentSwarm:
    """
    Hierarchical swarm orchestration engine managing agent role delegation, voting, and consensus.
    """

    def __init__(self):
        self.roles: Dict[str, SwarmAgentRole] = {}
        self._setup_default_roles()

    def _setup_default_roles(self) -> None:
        """Initialize standard hierarchical agent roles."""
        self.roles["architect"] = SwarmAgentRole(
            name="Architect",
            role_type="ARCHITECT",
            instructions="Decompose high-level goal into structured technical component sub-tasks.",
        )
        self.roles["coder"] = SwarmAgentRole(
            name="Coder",
            role_type="SPECIALIST",
            instructions="Write high-quality, typed, robust python code.",
        )
        self.roles["critic"] = SwarmAgentRole(
            name="Critic",
            role_type="CRITIC",
            instructions="Review code and outputs for safety, security, and bugs.",
        )
        self.roles["integrator"] = SwarmAgentRole(
            name="Integrator",
            role_type="INTEGRATOR",
            instructions="Merge and verify final multi-agent artifacts.",
        )

    def create_swarm_collaboration(self, goal: str) -> List[SwarmTaskAssignment]:
        """
        Decompose goal into a hierarchical swarm task pipeline.
        """
        logger.info(f"🐝 MultiAgentSwarm: Initiating collaboration for goal: '{goal}'")
        
        assignments = [
            SwarmTaskAssignment(
                task_id="swarm-1",
                assigned_role="architect",
                sub_goal=f"Design architecture specification for: {goal}",
            ),
            SwarmTaskAssignment(
                task_id="swarm-2",
                assigned_role="coder",
                sub_goal=f"Implement code components for: {goal}",
            ),
            SwarmTaskAssignment(
                task_id="swarm-3",
                assigned_role="critic",
                sub_goal=f"Review code and verify security compliance for: {goal}",
            ),
        ]
        return assignments

    def review_swarm_consensus(self, assignments: List[SwarmTaskAssignment]) -> bool:
        """
        Evaluate if all swarm steps have passed critic review.
        """
        all_approved = all(a.approved_by_critic for a in assignments)
        logger.info(f"🐝 MultiAgentSwarm: Consensus evaluation -> Approved: {all_approved}")
        return all_approved
