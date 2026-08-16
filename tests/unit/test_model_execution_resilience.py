# tests/unit/test_model_execution_resilience.py — Unit Tests for Model Execution & Resilience
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from brjarvis.gateway.client import ModelNotFoundError, ModelResponse, ProxyBrainClient, QuotaExceededError
from brjarvis.gateway.execution import ModelExecutionService
from brjarvis.gateway.health import ModelHealthService
from brjarvis.router.smart_router import ModelSelection, SmartModelRouter
from brjarvis.router.task_profile import TaskProfile


class TestModelExecutionResilience(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=ProxyBrainClient)
        self.mock_router = MagicMock(spec=SmartModelRouter)
        self.health_service = ModelHealthService()
        self.exec_service = ModelExecutionService(
            router=self.mock_router,
            client=self.mock_client,
            health_service=self.health_service,
            max_attempts=3
        )

    def test_successful_execution_records_telemetry(self):
        self.mock_router.route.return_value = ModelSelection(
            model_id="gemini-3.6-flash-high",
            provider="gemini",
            score=90.0,
            reason="Optimal general chat",
            fallback_models=["gemini-3.7-flash-tiered"]
        )
        self.mock_client.complete.return_value = ModelResponse(
            text="Hello world!",
            model="gemini-3.6-flash-high"
        )

        resp = self.exec_service.execute(messages=[{"role": "user", "content": "Hi"}])
        self.assertEqual(resp.text, "Hello world!")

        rec = self.health_service.get_health("gemini-3.6-flash-high")
        self.assertEqual(rec.success_count, 1)

    def test_failover_on_primary_model_quota_error(self):
        self.mock_router.route.return_value = ModelSelection(
            model_id="primary-failing-model",
            provider="gemini",
            score=85.0,
            reason="Primary candidate",
            fallback_models=["secondary-healthy-model"]
        )

        def side_effect(*args, **kwargs):
            m = kwargs.get("model", "")
            if m == "primary-failing-model":
                raise QuotaExceededError("Quota exhausted", model=m)
            return ModelResponse(
                text="Secondary candidate response",
                model=m
            )

        self.mock_client.complete.side_effect = side_effect

        resp = self.exec_service.execute(messages=[{"role": "user", "content": "Test prompt"}])
        self.assertEqual(resp.text, "Secondary candidate response")
        self.assertEqual(resp.model, "secondary-healthy-model")

        # Verify primary was flagged in health service
        self.assertFalse(self.health_service.is_available("primary-failing-model"))

    def test_json_repair_retry_flow(self):
        self.mock_router.route.return_value = ModelSelection(
            model_id="gemini-3.6-flash-high",
            provider="gemini",
            score=90.0,
            reason="Structured output task",
            fallback_models=[]
        )

        # First attempt returns malformed JSON, second repair attempt returns valid JSON
        responses = [
            ModelResponse(text="Here is your json: {status: invalid}", model="gemini-3.6-flash-high"),
            ModelResponse(text='{"status": "valid", "repaired": true}', model="gemini-3.6-flash-high")
        ]
        self.mock_client.complete.side_effect = responses

        resp = self.exec_service.execute(
            messages=[{"role": "user", "content": "Return json"}],
            json_mode=True
        )
        self.assertIn('"repaired": true', resp.text)


if __name__ == "__main__":
    unittest.main()
