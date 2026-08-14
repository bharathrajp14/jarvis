# tests/unit/test_model_benchmark.py — Unit Tests for Model Benchmark & Quality Scoring
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from gateway.capabilities import CapabilityState, ModelCapabilityRegistry
from gateway.client import ModelResponse, ProxyBrainClient
from gateway.health import ModelHealthService
from gateway.benchmark import BenchmarkScore, ModelBenchmarkService


class TestModelBenchmark(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=ProxyBrainClient)
        self.benchmark_service = ModelBenchmarkService(client=self.mock_client)

    def test_quality_score_calculation(self):
        score = BenchmarkScore(
            model_id="test-model",
            task_scores={"chat": 90.0, "reasoning": 85.0},
            schema_adherence_rate=0.95,
            tool_call_fidelity=0.90
        )
        quality = score.compute_quality_score()
        self.assertGreaterEqual(quality, 80.0)
        self.assertLessEqual(quality, 100.0)

    def test_structured_output_probe_success(self):
        self.mock_client.complete.return_value = ModelResponse(
            text='{"status": "ok", "code": 200}',
            model="structured-model"
        )

        success = self.benchmark_service.probe_structured_output("structured-model")
        self.assertTrue(success)

        caps = self.benchmark_service.capabilities.get_capabilities("structured-model")
        self.assertEqual(caps.structured_output, CapabilityState.SUPPORTED)

    def test_tool_calling_probe_success(self):
        self.mock_client.complete.return_value = ModelResponse(
            text="",
            tool_calls=[{"function": {"name": "lookup_weather", "arguments": '{"city": "Tokyo"}'}}],
            model="agentic-model"
        )

        success = self.benchmark_service.probe_tool_calling("agentic-model")
        self.assertTrue(success)

        caps = self.benchmark_service.capabilities.get_capabilities("agentic-model")
        self.assertEqual(caps.tool_calling, CapabilityState.SUPPORTED)
        self.assertEqual(caps.agentic, CapabilityState.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
