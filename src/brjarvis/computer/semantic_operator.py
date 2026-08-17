# computer/semantic_operator.py — Semantic Computer Operator for JARVIS MK37
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from .operator import get_computer_operator
from .types import ActionResult, ActionType, ComputerAction
from brjarvis.vision.engine import get_vision_engine
from brjarvis.vision.types import SemanticUIGraph, SemanticUINode, UIRole

logger = logging.getLogger("JARVIS.SemanticComputerOperator")


@dataclass
class SemanticTarget:
    """Semantic Target specification (zero pixel coordinates)."""

    component_name: str
    window_title: Optional[str] = None
    role: Optional[UIRole] = None
    occurrence_index: int = 0


class SemanticComputerOperator:
    """
    Semantic Computer Operator resolving high-level component targets
    to dynamic screen coordinates via the latest SemanticUIGraph.
    """

    def __init__(self):
        self.operator = get_computer_operator()
        self.vision = get_vision_engine()

    def click_component(self, target: SemanticTarget) -> ActionResult:
        """Resolve a semantic component target to coordinates and execute click."""
        return self._execute_semantic_action(target, ActionType.MOUSE_CLICK)

    def double_click_component(self, target: SemanticTarget) -> ActionResult:
        """Resolve a semantic component target to coordinates and execute double click."""
        return self._execute_semantic_action(target, ActionType.DOUBLE_CLICK)

    def right_click_component(self, target: SemanticTarget) -> ActionResult:
        """Resolve a semantic component target to coordinates and execute right click."""
        return self._execute_semantic_action(target, ActionType.RIGHT_CLICK)

    def type_into_component(self, target: SemanticTarget, text: str) -> ActionResult:
        """Click a target component to focus it, then type specified text."""
        click_res = self.click_component(target)
        if not click_res.success:
            return click_res
        return self.operator.type_text(text, description=f"Type into '{target.component_name}'")

    def _execute_semantic_action(self, target: SemanticTarget, action_type: ActionType) -> ActionResult:
        report = self.vision.analyze_screen(force_refresh=True)
        graph = report.semantic_graph

        if not graph:
            err_msg = f"Failed to construct SemanticUIGraph for target '{target.component_name}'"
            logger.error(f"❌ {err_msg}")
            return ActionResult(action_id="semantic_action", success=False, verification_message=err_msg)

        node = self._resolve_target_node(target, graph)
        if not node:
            err_msg = f"Could not locate semantic target component '{target.component_name}'"
            logger.warning(f"⚠️ {err_msg}")
            return ActionResult(action_id="semantic_action", success=False, verification_message=err_msg)

        center_x = node.bbox.center_x
        center_y = node.bbox.center_y

        logger.info(
            f"🖱️ Resolved target '{target.component_name}' ({node.role.value}) -> "
            f"Coordinates ({center_x}, {center_y})"
        )

        action = ComputerAction(
            action_type=action_type,
            x=center_x,
            y=center_y,
            description=f"{action_type.value} '{target.component_name}' at ({center_x}, {center_y})",
        )

        return self.operator.execute_action(action)

    def _resolve_target_node(
        self, target: SemanticTarget, graph: SemanticUIGraph
    ) -> Optional[SemanticUINode]:
        """Find matching node in SemanticUIGraph with exact or fuzzy substring matching."""
        target_clean = target.component_name.lower().strip()
        matches = graph.find_by_name(target_clean)
        
        # Fuzzy match fallback if exact name match returns nothing
        if not matches and graph.nodes:
            matches = [
                n for n in graph.nodes.values() 
                if target_clean in n.name.lower() or n.name.lower() in target_clean
            ]

        if target.role:
            matches = [m for m in matches if m.role == target.role]

        if matches and 0 <= target.occurrence_index < len(matches):
            return matches[target.occurrence_index]
        elif matches:
            return matches[0]

        return None


_global_semantic_operator: Optional[SemanticComputerOperator] = None


def get_semantic_operator() -> SemanticComputerOperator:
    global _global_semantic_operator
    if _global_semantic_operator is None:
        _global_semantic_operator = SemanticComputerOperator()
    return _global_semantic_operator
