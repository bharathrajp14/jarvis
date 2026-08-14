# tests/unit/test_model_capabilities.py — Unit Tests for Progressive Model Capabilities
from __future__ import annotations

import unittest

from gateway.capabilities import (
    CapabilityState,
    ModelCapabilities,
    ModelCapabilityRegistry,
)


class TestModelCapabilities(unittest.TestCase):

    def setUp(self):
        self.registry = ModelCapabilityRegistry()

    def test_provisional_profile_does_not_assume_name_is_fact(self):
        # A model named "agent" should still treat tool_calling as provisional/UNKNOWN until verified
        caps = self.registry.get_capabilities("random-agent-model")
        self.assertEqual(caps.tool_calling, CapabilityState.UNKNOWN)
        self.assertEqual(caps.structured_output, CapabilityState.UNKNOWN)

    def test_satisfies_requirements_enforcement(self):
        caps = ModelCapabilities(
            chat=CapabilityState.SUPPORTED,
            tool_calling=CapabilityState.UNSUPPORTED,
            vision=CapabilityState.SUPPORTED
        )

        # Chat and vision requirements pass
        ok, _ = caps.satisfies_requirements(requires_vision=True)
        self.assertTrue(ok)

        # Tool calling explicitly unsupported fails
        ok, reason = caps.satisfies_requirements(requires_tools=True)
        self.assertFalse(ok)
        self.assertIn("tool_calling", reason)

    def test_empirical_verification_updates_profile(self):
        model_id = "test-model-4.0"
        caps = self.registry.get_capabilities(model_id)
        self.assertEqual(caps.structured_output, CapabilityState.UNKNOWN)

        # Empirical test confirms structured output is supported
        self.registry.set_capability(model_id, "structured_output", CapabilityState.SUPPORTED)
        updated_caps = self.registry.get_capabilities(model_id)
        self.assertEqual(updated_caps.structured_output, CapabilityState.SUPPORTED)

    def test_image_generation_endpoints_classified_distinctly(self):
        img_model_id = "gemini-3-pro-image-2k-16x9"
        caps = self.registry.get_capabilities(img_model_id)
        # Dedicated image generation endpoints are marked chat=UNSUPPORTED
        self.assertEqual(caps.chat, CapabilityState.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
