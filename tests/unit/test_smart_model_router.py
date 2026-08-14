# tests/unit/test_smart_model_router.py — Unit Tests for Smart Proxy-Brain Model Router
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from gateway.discovery import DiscoveredModel, ModelDiscoveryService
from gateway.client import ModelResponse, ProxyBrainClient
from gateway.models_registry import ModelTier, TaskCapability
from router.smart_router import (
    ModelRequest,
    RoutingDecision,
    SmartModelRouter,
    get_smart_router,
)


class TestSmartModelRouter(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=ProxyBrainClient)
        self.mock_client.complete.return_value = ModelResponse(
            text="Simulated completion",
            model="gemini-3.6-flash-high",
            usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            latency_ms=120.0
        )
        self.mock_discovery = MagicMock(spec=ModelDiscoveryService)
        self.mock_discovery.discover_models.return_value = [
            DiscoveredModel(id="gemini-3.1-flash-lite", owned_by="google"),
            DiscoveredModel(id="gemini-3.6-flash-high", owned_by="google"),
            DiscoveredModel(id="gemini-3.7-flash-tiered", owned_by="google"),
            DiscoveredModel(id="gemini-3.1-pro-high", owned_by="google"),
            DiscoveredModel(id="gemini-3-flash-agent", owned_by="google"),
            DiscoveredModel(id="gemini-3.1-flash-image", owned_by="google"),
            DiscoveredModel(id="claude-opus-4-6-thinking", owned_by="anthropic"),
            DiscoveredModel(id="claude-sonnet-4-6", owned_by="anthropic")
        ]
        self.mock_discovery.get_model.side_effect = lambda m_id: DiscoveredModel(id=m_id, owned_by="google")
        self.router = SmartModelRouter(
            discovery_service=self.mock_discovery,
            client=self.mock_client,
            preferred_provider="gemini"
        )

    def test_route_simple_greeting_to_flash_lite(self):
        req = ModelRequest(
            task_type=TaskCapability.CHAT,
            messages=[{"role": "user", "content": "hi"}]
        )
        decision = self.router.route(req)
        self.assertEqual(decision.selected_model, "gemini-3.1-flash-lite")

    def test_route_complex_code_and_architecture_to_pro_high(self):
        req = ModelRequest(
            task_type=TaskCapability.CODE,
            messages=[{
                "role": "user",
                "content": "Analyze our microservice architecture, detect any deadlock in async def worker(), and refactor database transactions."
            }],
            complexity="high"
        )
        decision = self.router.route(req)
        self.assertIn(decision.selected_model, ("gemini-3.7-flash-tiered", "gemini-3.1-pro-high"))


    def test_route_agent_task_to_flash_agent(self):
        req = ModelRequest(
            task_type=TaskCapability.AGENT,
            messages=[{
                "role": "user",
                "content": "Open browser, navigate to site, find pricing table, and extract CSV."
            }],
            requires_tools=True,
            tools=[{"name": "browser_control"}]
        )
        decision = self.router.route(req)
        self.assertIn("agent", decision.selected_model)

    def test_route_vision_task_to_flash_image(self):
        req = ModelRequest(
            task_type=TaskCapability.VISION,
            messages=[{"role": "user", "content": "Extract OCR text from screenshot."}],
            requires_vision=True
        )
        decision = self.router.route(req)
        self.assertEqual(decision.selected_model, "gemini-3.1-flash-image")

    def test_manual_override_valid_model(self):
        success, msg = self.router.set_manual_override("gemini-3.7-flash-tiered")
        self.assertTrue(success)
        self.assertEqual(self.router.get_manual_override(), "gemini-3.7-flash-tiered")

        req = ModelRequest(
            task_type=TaskCapability.CHAT,
            messages=[{"role": "user", "content": "hello"}]
        )
        decision = self.router.route(req)
        self.assertEqual(decision.selected_model, "gemini-3.7-flash-tiered")

        # Reset override
        self.router.set_manual_override("auto")
        self.assertIsNone(self.router.get_manual_override())

    def test_manual_override_invalid_model_rejected(self):
        success, msg = self.router.set_manual_override("nonexistent-super-model")
        self.assertFalse(success)
        self.assertIn("Unknown model", msg)
        self.assertIsNone(self.router.get_manual_override())

    def test_dynamic_fallback_on_model_not_found(self):
        req = ModelRequest(
            task_type=TaskCapability.DEEP_REASONING,
            messages=[{"role": "user", "content": "Complex reasoning question"}]
        )
        resp = self.router.complete(req)
        self.assertEqual(resp.text, "Simulated completion")

        metrics = self.router.get_metrics()
        self.assertEqual(metrics["successful_requests"], 1)


if __name__ == "__main__":
    unittest.main()
