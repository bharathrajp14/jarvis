# computer/recovery.py — Self-Healing & Recovery Engine for JARVIS MK37
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from brjarvis.events.bus import get_event_bus
from brjarvis.events.types import BaseEvent
from brjarvis.vision.engine import get_vision_engine

from .semantic_operator import SemanticTarget, get_semantic_operator
from .types import ActionResult

logger = logging.getLogger("JARVIS.SelfHealingEngine")


class SelfHealingEngine:
    """
    Autonomous Self-Healing & Recovery Engine:
    On action failure or verification miss (window moved, unexpected popup),
    re-scans the SemanticUIGraph, closes unexpected dialogs, repositions targets,
    and retries execution without failing the master workflow.
    """

    def __init__(self, max_recovery_attempts: int = 3):
        self.semantic_operator = get_semantic_operator()
        self.vision = get_vision_engine()
        self.event_bus = get_event_bus()
        self.max_recovery_attempts = max_recovery_attempts

    def execute_with_self_healing(
        self, target: SemanticTarget, action_func: Optional[Callable[[], ActionResult]] = None
    ) -> ActionResult:
        """Execute a semantic action with self-healing recovery loops."""
        for attempt in range(1, self.max_recovery_attempts + 1):
            result = action_func() if action_func else self.semantic_operator.click_component(target)

            if result.success:
                self.event_bus.publish(
                    BaseEvent(
                        topic="verification.success", payload={"target": target.component_name, "attempt": attempt}
                    )
                )
                return result

            # Self-healing recovery attempt
            logger.warning(
                f"⚠️ Self-Healing Triggered (Attempt {attempt}/{self.max_recovery_attempts}): "
                f"Target '{target.component_name}' verification failed: {result.verification_message}"
            )
            self.event_bus.publish(
                BaseEvent(
                    topic="verification.failed",
                    payload={"target": target.component_name, "error": result.verification_message},
                )
            )

            # Step 1: Re-scan screen & check for unexpected popups
            report = self.vision.analyze_screen(force_refresh=True)
            if self._dismiss_unexpected_popups(report):
                time.sleep(0.3)
                continue

            # Step 2: Exponential backoff delay
            time.sleep(0.5 * attempt)

        self.event_bus.publish(BaseEvent(topic="action.recovery_failed", payload={"target": target.component_name}))
        return ActionResult(
            action_id="self_healing",
            success=False,
            verification_message=f"Self-healing exhausted {self.max_recovery_attempts} recovery attempts.",
        )

    def _dismiss_unexpected_popups(self, report) -> bool:
        """Inspect screen for popups or modal dialogs and dismiss them via click or Escape key."""
        graph = report.semantic_graph
        if not graph:
            return False

        # Look for dialog nodes
        dialogs = graph.find_by_name("dialog") or graph.find_by_name("popup")
        if dialogs:
            logger.info("🛡️ SelfHealingEngine: Unexpected dialog detected, attempting auto-dismissal.")
            # Search for close or cancel button
            cancel_btn = graph.find_by_name("cancel") or graph.find_by_name("close") or graph.find_by_name("dismiss")
            if cancel_btn:
                btn = cancel_btn[0]
                from brjarvis.computer.operator import get_computer_operator
                from brjarvis.computer.types import ActionType, ComputerAction

                get_computer_operator().execute_action(
                    ComputerAction(action_type=ActionType.MOUSE_CLICK, x=btn.bbox.center_x, y=btn.bbox.center_y)
                )
                return True
            else:
                # Fallback: send Escape key press to dismiss modal dialog
                from brjarvis.computer.operator import get_computer_operator
                from brjarvis.computer.types import ActionType, ComputerAction

                get_computer_operator().execute_action(
                    ComputerAction(action_type=ActionType.KEYBOARD_PRESS, keys=["escape"])
                )
                return True

        return False


_global_self_healing_engine: Optional[SelfHealingEngine] = None


def get_self_healing_engine() -> SelfHealingEngine:
    global _global_self_healing_engine
    if _global_self_healing_engine is None:
        _global_self_healing_engine = SelfHealingEngine()
    return _global_self_healing_engine
