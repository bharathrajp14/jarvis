# tests/unit/test_adaptive_router.py — Unit Tests for Adaptive Smart Model Router
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from gateway.discovery import DiscoveredModel, ModelDiscoveryService
from gateway.health import ModelHealthService
from router.smart_router import ModelSelection, SmartModelRouter
from router.task_profile import TaskComplexity, TaskProfile, TaskProfileClassifier


class TestAdaptiveRouter(unittest.TestCase):

    def setUp(self):
        self.mock_discovery = MagicMock(spec=ModelDiscoveryService)
        self.mock_discovery.discover_models.return_value = [
            DiscoveredModel(id="gemini-3.1-flash-lite", owned_by="google"),
            DiscoveredModel(id="gemini-3.6-flash-high", owned_by="google"),
            DiscoveredModel(id="gemini-3.7-flash-tiered", owned_by="google"),
            DiscoveredModel(id="gemini-3-flash-agent", owned_by="google"),
            DiscoveredModel(id="gemini-3.1-flash-image", owned_by="google"),
            DiscoveredModel(id="claude-opus-4-6-thinking", owned_by="anthropic"),
            DiscoveredModel(id="claude-sonnet-4-6", owned_by="anthropic"),
            DiscoveredModel(id="gpt-4o", owned_by="openai")
        ]
        self.health_service = ModelHealthService()
        self.router = SmartModelRouter(
            discovery_service=self.mock_discovery,
            health_service=self.health_service,
            preferred_provider="gemini"
        )

    def test_task_profile_classifier_greetings(self):
        profile = TaskProfileClassifier.classify(messages=[{"role": "user", "content": "hello"}])
        self.assertEqual(profile.task_type, "fast_chat")
        self.assertTrue(profile.latency_sensitive)
        self.assertEqual(profile.complexity, TaskComplexity.LOW)

    def test_task_profile_classifier_complex_code_and_reasoning(self):
        code_prompt = (
            "Analyze our distributed database replication protocol, find the race condition "
            "in async def acquire_lock():\n"
            "    async with self.lock:\n"
            "        return await tx.commit()\n"
            "and suggest architecture refactoring tradeoffs."
        )
        profile = TaskProfileClassifier.classify(messages=[{"role": "user", "content": code_prompt}])
        self.assertEqual(profile.task_type, "code")
        self.assertTrue(profile.requires_code)
        self.assertTrue(profile.requires_reasoning)
        self.assertEqual(profile.complexity, TaskComplexity.HIGH)

    def test_routing_fast_greeting_selects_flash_lite(self):
        profile = TaskProfile(task_type="fast_chat", complexity=TaskComplexity.LOW, latency_sensitive=True)
        selection = self.router.route(profile)
        self.assertEqual(selection.model_id, "gemini-3.1-flash-lite")
        self.assertGreater(selection.score, 60.0)

    def test_routing_complex_code_selects_high_reasoning_gemini(self):
        profile = TaskProfile(task_type="code", complexity=TaskComplexity.HIGH, requires_code=True, requires_reasoning=True)
        selection = self.router.route(profile)
        self.assertEqual(selection.model_id, "gemini-3.7-flash-tiered")

    def test_routing_agent_selects_agent_architecture(self):
        profile = TaskProfile(task_type="agent", complexity=TaskComplexity.HIGH, requires_tools=True, requires_agent=True)
        selection = self.router.route(profile)
        self.assertEqual(selection.model_id, "gemini-3-flash-agent")

    def test_routing_vision_selects_vision_model(self):
        profile = TaskProfile(task_type="vision", complexity=TaskComplexity.MEDIUM, requires_vision=True)
        selection = self.router.route(profile)
        self.assertEqual(selection.model_id, "gemini-3.1-flash-image")

    def test_circuit_broken_model_excluded_from_primary(self):
        # Trip circuit breaker for gemini-3.1-flash-lite
        self.health_service.record_failure("gemini-3.1-flash-lite", "Quota exhausted", is_quota=True)

        profile = TaskProfile(task_type="fast_chat", complexity=TaskComplexity.LOW, latency_sensitive=True)
        selection = self.router.route(profile)
        # Should smoothly fall back to next healthy model (e.g. gemini-3.6-flash-high)
        self.assertNotEqual(selection.model_id, "gemini-3.1-flash-lite")
        self.assertIn("gemini-3.6", selection.model_id)

    def test_manual_model_pinning(self):
        ok, msg = self.router.set_manual_override("claude-opus-4-6-thinking")
        self.assertTrue(ok)

        profile = TaskProfile(task_type="chat", complexity=TaskComplexity.MEDIUM)
        selection = self.router.route(profile)
        self.assertEqual(selection.model_id, "claude-opus-4-6-thinking")
        self.assertIn("Manual user override", selection.reason)

        # Reset to auto
        self.router.set_manual_override("auto")
        self.assertIsNone(self.router.get_manual_override())


if __name__ == "__main__":
    unittest.main()
