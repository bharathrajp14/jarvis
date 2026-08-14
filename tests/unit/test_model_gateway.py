# tests/unit/test_model_gateway.py — Unit Tests for OpenAI-Compatible ModelGateway
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from gateway.model_gateway import (
    GatewayAuthenticationError,
    GatewayTimeoutError,
    GatewayUnavailableError,
    MalformedResponseError,
    ModelGateway,
    ModelGatewayError,
    ModelNotFoundError,
    ModelResponse,
    _sanitize_error_msg,
)


class TestModelGateway(unittest.TestCase):

    def setUp(self):
        self.gateway = ModelGateway(
            base_url="http://localhost:8045/v1",
            api_key="test-proxy-key"
        )
        self.gateway._openai_client = None  # test direct HTTP client path

    def test_credential_sanitization(self):
        msg = "Failed with Bearer secret-token-12345 and api_key: supersecret"
        sanitized = _sanitize_error_msg(msg)
        self.assertNotIn("secret-token-12345", sanitized)
        self.assertNotIn("supersecret", sanitized)
        self.assertIn("[REDACTED]", sanitized)

    @patch("requests.post")
    def test_complete_successful_response(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{
                "message": {"content": "Hello from Proxy Brain", "role": "assistant"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }

        resp = self.gateway.complete(
            messages=[{"role": "user", "content": "Hello"}],
            model="gemini-3.6-flash-high"
        )

        self.assertIsInstance(resp, ModelResponse)
        self.assertEqual(resp.text, "Hello from Proxy Brain")
        self.assertEqual(resp.model, "gemini-3.6-flash-high")
        self.assertEqual(resp.usage["total_tokens"], 15)
        self.assertEqual(resp.provider, "proxy_brain")

    @patch("requests.post")
    def test_complete_model_not_found(self, mock_post):
        mock_post.return_value.status_code = 404
        mock_post.return_value.text = "Model not found"

        with self.assertRaises(ModelNotFoundError):
            self.gateway.complete(
                messages=[{"role": "user", "content": "Hello"}],
                model="nonexistent-model"
            )

    @patch("requests.post")
    def test_complete_auth_failure(self, mock_post):
        mock_post.return_value.status_code = 401
        mock_post.return_value.text = "Unauthorized"

        with self.assertRaises(GatewayAuthenticationError):
            self.gateway.complete(
                messages=[{"role": "user", "content": "Hello"}],
                model="gemini-3.6-flash-high"
            )

    @patch("requests.get")
    def test_discover_models(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"id": "gemini-3.6-flash-high"},
                {"id": "gemini-3.1-pro-high"},
                {"id": "claude-sonnet-4-6"}
            ]
        }

        models = self.gateway.discover_models(force_refresh=True)
        self.assertIn("gemini-3.6-flash-high", models)
        self.assertIn("gemini-3.1-pro-high", models)
        self.assertIn("claude-sonnet-4-6", models)

    def test_privacy_mode_blocks_direct_cloud(self):
        with self.assertRaises(ValueError):
            ModelGateway(
                base_url="https://api.openai.com/v1",
                api_key="sk-test"
            )


if __name__ == "__main__":
    unittest.main()
