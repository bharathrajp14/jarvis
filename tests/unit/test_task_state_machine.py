# tests/unit/test_task_state_machine.py — Unit Tests for Strict Task Lifecycle & State Transitions
from __future__ import annotations

import unittest
from agent.task_lifecycle import (
    CancellationToken,
    TaskContext,
    TaskState,
    TERMINAL_STATES,
)
from agent.task_queue import TaskQueue, TaskStatus, TaskPriority


class TestTaskStateMachine(unittest.TestCase):

    def test_valid_forward_transitions(self):
        ctx = TaskContext(task_id="t1", goal="sample goal")
        self.assertEqual(ctx.state, TaskState.QUEUED)

        self.assertTrue(ctx.transition_to(TaskState.RUNNING))
        self.assertEqual(ctx.state, TaskState.RUNNING)

        self.assertTrue(ctx.transition_to(TaskState.SUCCEEDED))
        self.assertEqual(ctx.state, TaskState.SUCCEEDED)

    def test_terminal_state_immutability(self):
        ctx = TaskContext(task_id="t2", goal="sample goal")
        ctx.transition_to(TaskState.RUNNING)
        ctx.transition_to(TaskState.FAILED, error_msg="Simulated failure")

        self.assertEqual(ctx.state, TaskState.FAILED)
        self.assertIn(ctx.state, TERMINAL_STATES)

        # Attempt illegal transition from FAILED to RUNNING
        self.assertFalse(ctx.transition_to(TaskState.RUNNING))
        self.assertEqual(ctx.state, TaskState.FAILED)

        # Attempt illegal transition from FAILED to SUCCEEDED
        self.assertFalse(ctx.transition_to(TaskState.SUCCEEDED))
        self.assertEqual(ctx.state, TaskState.FAILED)

    def test_cancellation_flow(self):
        ctx = TaskContext(task_id="t3", goal="sample cancel goal")
        ctx.transition_to(TaskState.RUNNING)
        self.assertTrue(ctx.transition_to(TaskState.CANCELLING))
        self.assertTrue(ctx.transition_to(TaskState.CANCELLED))
        self.assertEqual(ctx.state, TaskState.CANCELLED)
        self.assertFalse(ctx.transition_to(TaskState.SUCCEEDED))

    def test_cancellation_token(self):
        token = CancellationToken()
        self.assertFalse(token.is_cancelled)

        token.cancel("User abort")
        self.assertTrue(token.is_cancelled)
        self.assertEqual(token.reason, "User abort")

        with self.assertRaises(InterruptedError):
            token.check()


if __name__ == "__main__":
    unittest.main()
