# gateway/health.py — Model Health Tracking & Circuit Breaker Service
"""
Tracks real-time health, latency, failure rates, and circuit-breaker states
for all discovered models. Computes dynamic health_score to prevent hammering
unhealthy or quota-exhausted models.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("JARVIS.ModelHealth")


class HealthState(str, Enum):
    """Real-time health status of a model."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class ModelHealthRecord:
    """Historical telemetry and current health status for an individual model."""
    model_id: str
    state: HealthState = HealthState.UNKNOWN
    last_success: float = 0.0
    last_failure: float = 0.0
    latency_ms: float = 0.0  # Exponential moving average
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    timeout_count: int = 0
    quota_failure_count: int = 0
    last_error: str = ""
    circuit_open_until: float = 0.0

    def record_success(self, latency: float) -> None:
        now = time.time()
        self.last_success = now
        self.consecutive_failures = 0
        self.success_count += 1
        self.state = HealthState.AVAILABLE
        self.circuit_open_until = 0.0

        # Update EMA latency (alpha = 0.3)
        if self.latency_ms <= 0:
            self.latency_ms = latency
        else:
            self.latency_ms = 0.7 * self.latency_ms + 0.3 * latency

    def record_failure(self, error: str, is_timeout: bool = False, is_quota: bool = False, cooldown_seconds: float = 60.0) -> None:
        now = time.time()
        self.last_failure = now
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_error = error

        if is_timeout:
            self.timeout_count += 1
        if is_quota:
            self.quota_failure_count += 1

        # Trip circuit breaker on repeated failures or quota exhaustion
        if is_quota or self.consecutive_failures >= 3:
            self.state = HealthState.UNAVAILABLE
            self.circuit_open_until = now + cooldown_seconds
            logger.warning(f"[CircuitBreaker] Tripped for '{self.model_id}': {error} (cooldown: {cooldown_seconds}s)")
        elif self.consecutive_failures >= 1:
            self.state = HealthState.DEGRADED

    def is_circuit_open(self) -> bool:
        """Return True if circuit breaker is currently preventing execution."""
        if self.circuit_open_until <= 0:
            return False
        if time.time() < self.circuit_open_until:
            return True
        # Cooldown expired, transition to half-open trial
        self.circuit_open_until = 0.0
        self.state = HealthState.DEGRADED
        return False


    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0 if self.state == HealthState.AVAILABLE else 0.5
        return self.success_count / total

    def compute_health_score(self) -> float:
        """
        Dynamic health score (0.0 to 100.0).
        Penalizes latency, recent failures, and active circuit breakers.
        """
        if self.is_circuit_open() or self.state == HealthState.UNAVAILABLE:
            return 0.0

        score = 50.0  # Baseline

        # Availability state
        if self.state == HealthState.AVAILABLE:
            score += 30.0
        elif self.state == HealthState.DEGRADED:
            score += 10.0

        # Success rate factor (+20 to -20)
        score += (self.success_rate - 0.5) * 40.0

        # Latency factor (penalize > 8s, reward < 4s)
        if self.latency_ms > 0:
            if self.latency_ms < 3000:
                score += 10.0
            elif self.latency_ms < 6000:
                score += 5.0
            elif self.latency_ms > 10000:
                score -= 20.0
            elif self.latency_ms > 7000:
                score -= 10.0

        # Penalty for recent consecutive failures
        score -= min(30.0, self.consecutive_failures * 10.0)

        return max(0.0, min(100.0, score))


class ModelHealthService:
    """
    Centralized health registry and circuit breaker manager.
    """

    def __init__(self, default_cooldown_seconds: float = 60.0):
        self.cooldown_seconds = default_cooldown_seconds
        self._records: dict[str, ModelHealthRecord] = {}
        self._lock = threading.RLock()

    def get_health(self, model_id: str) -> ModelHealthRecord:
        with self._lock:
            if model_id not in self._records:
                self._records[model_id] = ModelHealthRecord(model_id=model_id)
            return self._records[model_id]

    def record_success(self, model_id: str, latency_ms: float = 0.0, latency: Optional[float] = None) -> None:
        actual_lat = latency if latency is not None else latency_ms
        with self._lock:
            rec = self.get_health(model_id)
            rec.record_success(actual_lat)


    def record_failure(
        self,
        model_id: str,
        error: str,
        is_timeout: bool = False,
        is_quota: bool = False
    ) -> None:
        with self._lock:
            rec = self.get_health(model_id)
            rec.record_failure(error, is_timeout=is_timeout, is_quota=is_quota, cooldown_seconds=self.cooldown_seconds)

    def is_available(self, model_id: str) -> bool:
        """Check if model is currently considered viable for routing."""
        with self._lock:
            rec = self.get_health(model_id)
            return not rec.is_circuit_open() and rec.state != HealthState.UNAVAILABLE

    def get_health_score(self, model_id: str) -> float:
        with self._lock:
            return self.get_health(model_id).compute_health_score()

    def reset_circuit_breaker(self, model_id: str) -> None:
        """Manually clear circuit breaker for a model."""
        with self._lock:
            rec = self.get_health(model_id)
            rec.circuit_open_until = 0.0
            rec.consecutive_failures = 0
            rec.state = HealthState.UNKNOWN


_global_health_service: Optional[ModelHealthService] = None


def get_health_service() -> ModelHealthService:
    """Return the global ModelHealthService singleton."""
    global _global_health_service
    if _global_health_service is None:
        _global_health_service = ModelHealthService()
    return _global_health_service
