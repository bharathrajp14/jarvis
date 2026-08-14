# tests/unit/test_model_health_circuit_breaker.py — Unit Tests for Health & Circuit Breakers
from __future__ import annotations

import time
import unittest

from gateway.health import HealthState, ModelHealthRecord, ModelHealthService


class TestModelHealthCircuitBreaker(unittest.TestCase):

    def setUp(self):
        self.health_service = ModelHealthService(default_cooldown_seconds=1.0)

    def test_latency_exponential_moving_average(self):
        rec = ModelHealthRecord(model_id="test-model")
        rec.record_success(latency=100.0)
        self.assertEqual(rec.latency_ms, 100.0)

        # Subsequent success updates EMA (0.7 * 100 + 0.3 * 200 = 130.0)
        rec.record_success(latency=200.0)
        self.assertAlmostEqual(rec.latency_ms, 130.0, places=1)

    def test_circuit_breaker_trips_on_consecutive_failures(self):
        model_id = "failing-model"
        self.health_service.record_failure(model_id, "Error 1")
        self.assertTrue(self.health_service.is_available(model_id))  # Degraded but available

        self.health_service.record_failure(model_id, "Error 2")
        self.assertTrue(self.health_service.is_available(model_id))

        self.health_service.record_failure(model_id, "Error 3")  # Threshold = 3
        # Circuit breaker should now be OPEN / UNAVAILABLE
        self.assertFalse(self.health_service.is_available(model_id))
        self.assertEqual(self.health_service.get_health_score(model_id), 0.0)

    def test_circuit_breaker_trips_immediately_on_quota_error(self):
        model_id = "quota-exhausted-model"
        self.health_service.record_failure(model_id, "HTTP 503 No accounts with quota", is_quota=True)
        self.assertFalse(self.health_service.is_available(model_id))
        self.assertEqual(self.health_service.get_health(model_id).state, HealthState.UNAVAILABLE)

    def test_circuit_breaker_cooldown_and_recovery(self):
        model_id = "recovering-model"
        # Trip circuit breaker with short cooldown (0.2s)
        self.health_service.cooldown_seconds = 0.2
        self.health_service.record_failure(model_id, "Quota exhausted", is_quota=True)
        self.assertFalse(self.health_service.is_available(model_id))

        # Wait for cooldown to expire
        time.sleep(0.3)
        self.assertTrue(self.health_service.is_available(model_id))

        # Success resets circuit breaker to healthy
        self.health_service.record_success(model_id, latency=150.0)
        rec = self.health_service.get_health(model_id)
        self.assertEqual(rec.state, HealthState.AVAILABLE)
        self.assertEqual(rec.consecutive_failures, 0)
        self.assertGreater(rec.compute_health_score(), 70.0)


if __name__ == "__main__":
    unittest.main()
