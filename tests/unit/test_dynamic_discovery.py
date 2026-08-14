# tests/unit/test_dynamic_discovery.py — Unit Tests for Dynamic Model Discovery
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from gateway.client import ProxyBrainClient
from gateway.discovery import DiscoveredModel, ModelDiscoveryService


class TestDynamicDiscovery(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=ProxyBrainClient)
        self.mock_client.base_url = "http://localhost:8045/v1"
        self.mock_client.api_key = "test-proxy-key"
        self.mock_client.timeout = 5.0
        self.service = ModelDiscoveryService(client=self.mock_client, cache_ttl_seconds=60.0)

    @patch("requests.get")
    def test_discover_models_parsing(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"id": "gemini-3.6-flash-high", "object": "model", "owned_by": "google"},
                {"id": "claude-sonnet-4-6", "object": "model", "owned_by": "anthropic"},
                {"id": "gpt-4o", "object": "model", "owned_by": "openai"}
            ]
        }

        models = self.service.discover_models(force_refresh=True)
        self.assertEqual(len(models), 3)

        m_dict = {m.id: m for m in models}
        self.assertIn("gemini-3.6-flash-high", m_dict)
        self.assertEqual(m_dict["gemini-3.6-flash-high"].provider, "gemini")
        self.assertEqual(m_dict["claude-sonnet-4-6"].provider, "anthropic")
        self.assertEqual(m_dict["gpt-4o"].provider, "openai")

    @patch("requests.get")
    def test_ttl_cache_avoids_redundant_calls(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"id": "gemini-3.6-flash-high"}]
        }

        # First call hits network
        self.service.discover_models()
        self.assertEqual(mock_get.call_count, 1)

        # Second call within TTL uses memory cache
        self.service.discover_models()
        self.assertEqual(mock_get.call_count, 1)

        # Force refresh hits network again
        self.service.discover_models(force_refresh=True)
        self.assertEqual(mock_get.call_count, 2)

    @patch("requests.get")
    def test_handles_dynamic_gateway_changes(self, mock_get):
        mock_get.return_value.status_code = 200
        # Initial inventory
        mock_get.return_value.json.return_value = {
            "data": [{"id": "gemini-3.6-flash-high"}]
        }
        self.service.discover_models(force_refresh=True)
        self.assertTrue(self.service.is_model_discovered("gemini-3.6-flash-high"))
        self.assertFalse(self.service.is_model_discovered("gemini-3.7-flash-tiered"))

        # Gateway dynamically adds a model
        mock_get.return_value.json.return_value = {
            "data": [
                {"id": "gemini-3.6-flash-high"},
                {"id": "gemini-3.7-flash-tiered"}
            ]
        }
        self.service.refresh()
        self.assertTrue(self.service.is_model_discovered("gemini-3.7-flash-tiered"))

    @patch("requests.get")
    def test_network_failure_returns_cached_fallback(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"id": "gemini-3.6-flash-high"}]
        }
        self.service.discover_models(force_refresh=True)

        # Now simulate network failure
        mock_get.side_effect = Exception("Gateway unreachable")
        models = self.service.discover_models(force_refresh=True)
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0].id, "gemini-3.6-flash-high")


if __name__ == "__main__":
    unittest.main()
