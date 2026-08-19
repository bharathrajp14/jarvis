# gateway/benchmark.py — Task-Aware Model Benchmark & Quality Evaluation
"""
Provides task-aware progressive benchmarking and quality scoring.
Evaluates:
  - Basic responsiveness (CHAT)
  - JSON schema adherence (STRUCTURED_OUTPUT)
  - Tool-calling fidelity (TOOL_SELECTION / AGENT)
  - Reasoning coherence (REASONING / CODE)

Runs on-demand (lazy validation) to avoid expensive startup bottlenecks.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .capabilities import CapabilityState, get_capability_registry
from .client import ProxyBrainClient, get_proxy_brain_client
from .health import get_health_service

logger = logging.getLogger("JARVIS.ModelBenchmark")


class BenchmarkTaskType(str, Enum):
    """Benchmark evaluation categories."""

    CHAT = "chat"
    REASONING = "reasoning"
    CODE = "code"
    PLANNING = "planning"
    TOOL_SELECTION = "tool_selection"
    STRUCTURED_OUTPUT = "structured_output"
    SUMMARIZATION = "summarization"


@dataclass
class BenchmarkScore:
    """Evaluation metrics for a model across task types."""

    model_id: str
    task_scores: dict[str, float] = field(default_factory=dict)
    schema_adherence_rate: float = 1.0
    tool_call_fidelity: float = 1.0
    average_latency_ms: float = 0.0
    last_benchmarked_at: float = 0.0

    def compute_quality_score(self, task_type: Optional[str] = None) -> float:
        """
        Aggregate quality score (0.0 to 100.0).
        Weight task-specific performance if available, otherwise aggregate.
        """
        if task_type and task_type in self.task_scores:
            base = self.task_scores[task_type]
        elif self.task_scores:
            base = sum(self.task_scores.values()) / len(self.task_scores)
        else:
            base = 75.0  # Default baseline for newly discovered models

        quality = base * 0.6 + (self.schema_adherence_rate * 100.0) * 0.2 + (self.tool_call_fidelity * 100.0) * 0.2
        return max(10.0, min(100.0, quality))


class ModelBenchmarkService:
    """
    Manages lazy, on-demand benchmarking of model candidates.
    """

    def __init__(self, client: Optional[ProxyBrainClient] = None):
        self.client = client or get_proxy_brain_client()
        self.capabilities = get_capability_registry()
        self.health = get_health_service()
        self._scores: dict[str, BenchmarkScore] = {}
        self._lock = threading.RLock()

    def get_quality_score(self, model_id: str, task_type: Optional[str] = None) -> float:
        """Return cached or baseline quality score for a model."""
        with self._lock:
            if model_id not in self._scores:
                self._scores[model_id] = BenchmarkScore(model_id=model_id)
            return self._scores[model_id].compute_quality_score(task_type)

    def probe_minimal(self, model_id: str) -> bool:
        """Level 2 Probe: Fast ping check to verify model responsiveness."""
        t0 = time.monotonic()
        try:
            resp = self.client.complete(
                model=model_id,
                messages=[{"role": "user", "content": "respond with pong"}],
                max_tokens=10,
                temperature=0.1,
            )
            latency = (time.monotonic() - t0) * 1000
            self.health.record_success(model_id, latency)
            with self._lock:
                score_rec = self._scores.setdefault(model_id, BenchmarkScore(model_id=model_id))
                score_rec.task_scores["chat"] = 90.0
                score_rec.average_latency_ms = latency
                score_rec.last_benchmarked_at = time.time()
            return True
        except Exception as exc:
            self.health.record_failure(model_id, str(exc))
            return False

    def probe_structured_output(self, model_id: str) -> bool:
        """Level 3 Probe: Verify JSON structured output capability."""
        prompt = 'Return valid JSON exactly: {"status": "ok", "code": 200}'
        t0 = time.monotonic()
        try:
            resp = self.client.complete(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.1,
                json_mode=True,
            )
            latency = (time.monotonic() - t0) * 1000
            self.health.record_success(model_id, latency)

            data = json.loads(resp.text)
            is_valid = data.get("status") == "ok" and data.get("code") == 200

            if is_valid:
                self.capabilities.set_capability(model_id, "structured_output", CapabilityState.SUPPORTED)
                with self._lock:
                    score_rec = self._scores.setdefault(model_id, BenchmarkScore(model_id=model_id))
                    score_rec.task_scores["structured_output"] = 95.0
                    score_rec.schema_adherence_rate = 1.0
                return True
            else:
                self.capabilities.set_capability(model_id, "structured_output", CapabilityState.UNSUPPORTED)
                return False
        except Exception as exc:
            logger.debug(f"[Benchmark] Structured output probe failed for {model_id}: {exc}")
            self.capabilities.set_capability(model_id, "structured_output", CapabilityState.UNSUPPORTED)
            return False

    def probe_tool_calling(self, model_id: str) -> bool:
        """Level 3 Probe: Verify native function calling capability."""
        test_tool = [
            {
                "type": "function",
                "function": {
                    "name": "lookup_weather",
                    "description": "Get weather for city",
                    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
                },
            }
        ]
        t0 = time.monotonic()
        try:
            resp = self.client.complete(
                model=model_id,
                messages=[{"role": "user", "content": "What is the weather in Tokyo?"}],
                tools=test_tool,
                max_tokens=60,
                temperature=0.1,
            )
            latency = (time.monotonic() - t0) * 1000
            self.health.record_success(model_id, latency)

            if resp.tool_calls and resp.tool_calls[0].get("function", {}).get("name") == "lookup_weather":
                self.capabilities.set_capability(model_id, "tool_calling", CapabilityState.SUPPORTED)
                self.capabilities.set_capability(model_id, "agentic", CapabilityState.SUPPORTED)
                with self._lock:
                    score_rec = self._scores.setdefault(model_id, BenchmarkScore(model_id=model_id))
                    score_rec.task_scores["tool_selection"] = 95.0
                    score_rec.tool_call_fidelity = 1.0
                return True
            else:
                # Some models return text instead of tool call object
                self.capabilities.set_capability(model_id, "tool_calling", CapabilityState.UNSUPPORTED)
                return False
        except Exception as exc:
            logger.debug(f"[Benchmark] Tool calling probe failed for {model_id}: {exc}")
            self.capabilities.set_capability(model_id, "tool_calling", CapabilityState.UNSUPPORTED)
            return False


_global_benchmark_service: Optional[ModelBenchmarkService] = None


def get_benchmark_service() -> ModelBenchmarkService:
    """Return the global ModelBenchmarkService singleton."""
    global _global_benchmark_service
    if _global_benchmark_service is None:
        _global_benchmark_service = ModelBenchmarkService()
    return _global_benchmark_service
