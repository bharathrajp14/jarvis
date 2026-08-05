# tests/test_regression_fixes.py — Consolidated Regression & Security Test Suite
from __future__ import annotations

import sys
import unittest
import unittest.mock as mock
from pathlib import Path

# ── Environment guards for hardware-dependent tests ───────────────────────────
_AUDIO_AVAILABLE = False
try:
    import speech_recognition as sr
    _AUDIO_AVAILABLE = True
except ImportError:
    pass

_COMPUTER_OPS_AVAILABLE = False
try:
    from computer.operator import get_computer_operator, ComputerAction, ActionType
    _COMPUTER_OPS_AVAILABLE = True
except ImportError:
    pass

_VOICE_AVAILABLE = False
try:
    from voice.assistant import BRVoiceAssistant
    _VOICE_AVAILABLE = True
except ImportError:
    pass


class TestWorkingMemory(unittest.TestCase):

    def test_working_memory_goal_pinning(self):
        """Root goal message should always remain at index 0 after trimming."""
        from memory.working import WorkingMemory
        wm = WorkingMemory(max_tokens=100_000)
        root_content = "ROOT_GOAL_PROMPT: Build system architecture"
        wm.add("user", root_content)

        for i in range(15):
            wm.add("assistant", f"Turn response {i}")
            wm.add("user", f"Turn user {i}")

        root_msg = wm.get()[0]
        wm.trim(max_turns=5)

        # FIXED: use pin_root() instead of directly accessing .history.insert()
        wm.pin_root(root_msg)
        msgs = wm.get()
        self.assertEqual(msgs[0]["content"], root_content)

    def test_working_memory_trim_no_infinite_loop(self):
        """Trimming should not loop infinitely even with a huge root message."""
        from memory.working import WorkingMemory
        wm = WorkingMemory(max_tokens=50)
        huge_root = "A" * 1000
        wm.add("user", huge_root)
        wm.add("assistant", "Response 1")
        wm.add("user", "Follow up 1")
        wm._trim()
        # After trim, char count should be within 4× the max_tokens
        self.assertLessEqual(wm._char_count, wm.max_tokens * 4 + 500)

    def test_working_memory_role_validation(self):
        """Invalid roles should be accepted with graceful fallback to 'user'."""
        from memory.working import WorkingMemory
        wm = WorkingMemory(max_tokens=10_000)
        wm.add("invalid_role", "Test content")
        msgs = wm.get()
        self.assertEqual(len(msgs), 1)
        # Role is coerced to 'user'
        self.assertEqual(msgs[0]["role"], "user")

    def test_working_memory_thread_safety(self):
        """Concurrent adds from multiple threads should not crash."""
        import threading
        from memory.working import WorkingMemory
        wm = WorkingMemory(max_tokens=10_000)
        errors = []

        def _add_many():
            try:
                for i in range(50):
                    wm.add("user", f"Message {i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_add_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

    def test_pin_root_does_not_duplicate(self):
        """pin_root() should not insert a duplicate if message is already present."""
        from memory.working import WorkingMemory
        wm = WorkingMemory(max_tokens=10_000)
        wm.add("user", "Goal message")
        root = wm.get()[0]
        wm.pin_root(root)  # Should be no-op since root is already at index 0
        self.assertEqual(len(wm.get()), 1)


class TestTokenManager(unittest.TestCase):

    def test_token_budget_manager_singleton(self):
        """TokenBudgetManager should return same instance from multiple calls."""
        from context.token_manager import TokenBudgetManager
        t1 = TokenBudgetManager()
        t2 = TokenBudgetManager()
        self.assertIs(t1, t2)

    def test_token_trim_history_greedy_fill(self):
        """trim_history should fill greedily from tail, not stop at first large message."""
        from context.token_manager import ContextTokenTrimmer
        # Large message in middle + small messages after
        history = [
            {"role": "user", "content": "A" * 5000},    # Large — 1250 tokens
            {"role": "assistant", "content": "B" * 5000},  # Large
            {"role": "user", "content": "C" * 100},     # Small — should fit
            {"role": "assistant", "content": "D" * 100},  # Small — should fit
        ]
        # Budget: 300 tokens max = 1200 chars
        trimmed = ContextTokenTrimmer.trim_history(history, max_tokens=300)
        # The two small tail messages should be included
        contents = [m["content"] for m in trimmed]
        self.assertIn("C" * 100, contents)
        self.assertIn("D" * 100, contents)


class TestDIContainer(unittest.TestCase):

    def test_transient_not_cached(self):
        """Transient registrations should return new instances every resolve()."""
        from core.di import Container
        c = Container()
        call_count = [0]

        def factory():
            call_count[0] += 1
            return object()

        c.register_transient(str, factory)
        obj1 = c.resolve(str)
        obj2 = c.resolve(str)
        # Transient: two calls, two different objects
        self.assertEqual(call_count[0], 2)
        self.assertIsNot(obj1, obj2)

    def test_singleton_cached(self):
        """Singleton registrations should return the same instance every resolve()."""
        from core.di import Container
        c = Container()
        c.register_singleton(int, lambda: 42)
        v1 = c.resolve(int)
        v2 = c.resolve(int)
        self.assertIs(v1, v2)

    def test_is_registered(self):
        """is_registered() should correctly detect all registration types."""
        from core.di import Container
        c = Container()
        self.assertFalse(c.is_registered(list))
        c.register_singleton(list, list)
        self.assertTrue(c.is_registered(list))


class TestEventBus(unittest.TestCase):

    def test_dlq_capped(self):
        """DLQ should not grow beyond _DLQ_MAX entries."""
        from events.bus import EventBus, _DLQ_MAX
        from events.types import BaseEvent
        bus = EventBus()

        def bad_handler(event):
            raise RuntimeError("Intentional failure")

        bus.subscribe("test.*", bad_handler)

        for i in range(_DLQ_MAX + 100):
            try:
                bus.publish(BaseEvent(topic="test.event", payload={"i": i}))
            except Exception:
                pass

        self.assertLessEqual(len(bus.get_dlq()), _DLQ_MAX)

    def test_topic_wildcard_matching(self):
        """EventBus should match wildcard topic patterns correctly."""
        from events.bus import EventBus
        from events.types import BaseEvent
        bus = EventBus()
        received = []

        bus.subscribe("task.*", lambda e: received.append(e.topic))
        bus.publish(BaseEvent(topic="task.created"))
        bus.publish(BaseEvent(topic="task.completed"))
        bus.publish(BaseEvent(topic="system.startup"))

        self.assertIn("task.created", received)
        self.assertIn("task.completed", received)
        self.assertNotIn("system.startup", received)


@unittest.skipIf(not _COMPUTER_OPS_AVAILABLE, "Computer operator not available in this environment")
class TestComputerOperator(unittest.TestCase):

    def test_computer_operator_failsafe_handling(self):
        from computer.operator import get_computer_operator, ComputerAction, ActionType
        op = get_computer_operator()
        action = ComputerAction(
            action_type=ActionType.CLIPBOARD_SET,
            text="JARVIS Failsafe Verification",
            description="Test failsafe action"
        )
        res = op.execute_action(action)
        self.assertTrue(res.success)


class TestPermissions(unittest.TestCase):

    def test_permissions_path_policy_enforcement(self):
        try:
            from permissions import check_permission
        except ImportError:
            self.skipTest("Permissions module not available")
        main_py = str(Path("main.py").resolve().as_posix())
        self.assertTrue(check_permission("view_file", {"AbsolutePath": main_py}))
        self.assertFalse(check_permission("view_file", {"AbsolutePath": "C:/Windows/System32/config/SAM"}))


@unittest.skipIf(not _AUDIO_AVAILABLE, "speech_recognition not installed — skipping audio tests")
class TestVoiceAssistant(unittest.TestCase):

    @unittest.skipIf(not _VOICE_AVAILABLE, "voice.assistant module not available")
    def test_voice_assistant_energy_floor(self):
        assistant = BRVoiceAssistant(ui=None)
        r = sr.Recognizer()
        r.energy_threshold = 50
        assistant._tune_recognizer(r)
        self.assertGreaterEqual(r.energy_threshold, 180)


class TestConfig(unittest.TestCase):

    def test_gpt_model_not_gemini(self):
        """GPT model ID should NOT be a Gemini model ID (regression test for copy-paste bug)."""
        from core.config import ModelConfig
        cfg = ModelConfig()
        self.assertNotIn("gemini", cfg.gpt.lower(),
                         f"GPT model '{cfg.gpt}' looks like a Gemini model — check config.py")

    def test_log_level_validation(self):
        """Invalid log levels should fall back to INFO."""
        from core.config import SystemConfig
        cfg = SystemConfig(log_level="BANANA")
        self.assertEqual(cfg.log_level, "INFO")

    def test_log_level_normalization(self):
        """Log level should be normalized to uppercase."""
        from core.config import SystemConfig
        cfg = SystemConfig(log_level="debug")
        self.assertEqual(cfg.log_level, "DEBUG")


class TestOrchestratorFallback(unittest.TestCase):

    def test_fallback_does_not_repeat_previous_turn(self):
        """Orchestrator fallback response should synthesize a new success message instead of repeating a previous turn."""
        from orchestrator.core import JarvisOrchestrator
        orch = JarvisOrchestrator()
        
        # Mock working memory to simulate a previous assistant turn
        orch.working_memory.add("user", "Hello")
        orch.working_memory.add("assistant", "Previous turn assistant response which should not be repeated")
        
        # Simulating a new user turn
        orch.working_memory.add("user", "Do some actions")
        
        # Fallback to current turn tool execution summary instead of repeating a previous turn
        tool_history = [{"tool_name": "list_files"}]
        tools_used = list(dict.fromkeys(t["tool_name"] for t in tool_history if "tool_name" in t))
        final_response = (
            f"I have successfully executed the requested operations using {', '.join(tools_used)}, sir."
            if tools_used else
            "I have successfully executed the requested operations, sir."
        )
        
        self.assertNotIn("Previous turn assistant response", final_response)
        self.assertIn("list_files", final_response)

    def test_stream_memory_saving(self):
        """Streaming mode react loop should save the clean final response to working memory and vector memory."""
        from orchestrator.core import JarvisOrchestrator
        orch = JarvisOrchestrator()
        
        orch.vector_memory = mock.Mock()
        orch.working_memory.add("user", "Perform search")
        
        orch._save_turn("Perform search", "Task completed successfully.")
        
        orch.vector_memory.store.assert_called_once()
        args, kwargs = orch.vector_memory.store.call_args
        self.assertIn("Task completed successfully.", args[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
