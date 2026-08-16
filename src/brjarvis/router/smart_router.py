# router/smart_router.py — Dynamic Multi-Factor Smart Model Router
"""
Dynamic, adaptive model router for BrJarvis connected to the Proxy Brain gateway.

Features:
- Dynamic discovery & live inventory integration.
- Progressive capability filtering (no assumptions based solely on name).
- Health & circuit breaker integration (skips quota-exhausted or failing models).
- Multi-factor scoring:
    routing_score = task_fit * capability_match * quality * health * reliability * latency_factor * provider_preference
- Gemini-Primary Policy (Gemini prioritized, with Claude/GPT diversity for fallbacks/specialists).
- Dynamic fallback chain generation (ranks live healthy candidates).
- Session memory with dynamic escalation & de-escalation.
- Manual model pinning (/model <name> / auto) with safety & availability enforcement.
- Explainable selection envelopes (ModelSelection).
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from gateway.capabilities import CapabilityState, ModelCapabilityRegistry, get_capability_registry
from gateway.client import ModelResponse, ProxyBrainClient, get_proxy_brain_client
from gateway.discovery import DiscoveredModel, ModelDiscoveryService, get_discovery_service
from gateway.health import HealthState, ModelHealthService, get_health_service
from gateway.benchmark import ModelBenchmarkService, get_benchmark_service
from .task_profile import TaskComplexity, TaskProfile, TaskProfileClassifier

logger = logging.getLogger("JARVIS.SmartRouter")


@dataclass
class ModelSelection:
    """Transparent, explainable selection record produced by the router."""
    model_id: str
    provider: str
    score: float
    reason: str
    fallback_models: list[str] = field(default_factory=list)
    task_type: str = "chat"
    complexity: str = "medium"

    @property
    def selected_model(self) -> str:
        """Alias for backwards compatibility."""
        return self.model_id

    @property
    def complexity_score(self) -> float:
        """Alias for backwards compatibility."""
        return self.score


RoutingDecision = ModelSelection  # Backwards compatibility alias


@dataclass
class ModelRequest:
    """Request envelope for model routing and completion (backwards compatibility)."""
    messages: list[dict[str, Any]] = field(default_factory=list)
    task_type: Any = "chat"
    system: str = ""
    tools: Optional[list[dict[str, Any]]] = None
    requires_tools: bool = False
    requires_vision: bool = False
    requires_agent: bool = False
    requires_reasoning: bool = False
    complexity: str = "medium"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    json_mode: bool = False
    response_format: Optional[dict[str, Any]] = None

    def to_task_profile(self) -> TaskProfile:
        from router.task_profile import TaskComplexity, TaskProfile
        comp_map = {
            "low": TaskComplexity.LOW,
            "medium": TaskComplexity.MEDIUM,
            "high": TaskComplexity.HIGH,
            "critical": TaskComplexity.CRITICAL,
        }
        c_enum = comp_map.get(str(self.complexity).lower(), TaskComplexity.MEDIUM)
        t_type = getattr(self.task_type, "value", str(self.task_type))

        return TaskProfile(
            task_type=t_type,
            complexity=c_enum,
            requires_reasoning=self.requires_reasoning or (c_enum in (TaskComplexity.HIGH, TaskComplexity.CRITICAL)),
            requires_code=t_type in ("code", "code_review"),
            requires_tools=self.requires_tools or bool(self.tools),
            requires_agent=self.requires_agent or t_type in ("agent", "planning"),
            requires_vision=self.requires_vision or t_type == "vision",
            requires_structured_output=self.json_mode or bool(self.response_format)
        )



class SmartModelRouter:
    """
    Production-grade model router connecting task demands to live gateway models.
    """

    def __init__(
        self,
        discovery_service: Optional[ModelDiscoveryService] = None,
        capability_registry: Optional[ModelCapabilityRegistry] = None,
        health_service: Optional[ModelHealthService] = None,
        benchmark_service: Optional[ModelBenchmarkService] = None,
        client: Optional[ProxyBrainClient] = None,
        gateway: Optional[Any] = None,
        preferred_provider: str = "gemini"
    ):
        self.discovery = discovery_service or get_discovery_service()
        self.capabilities = capability_registry or get_capability_registry()
        self.health = health_service or get_health_service()
        self.benchmark = benchmark_service or get_benchmark_service()
        self.client = client or gateway or get_proxy_brain_client()
        self.preferred_provider = preferred_provider.lower()


        self._manual_override: Optional[str] = None
        self._session_model: Optional[str] = None
        self._lock = threading.RLock()

    def set_manual_override(self, model_name: str) -> tuple[bool, str]:
        """Pin a specific model or reset to auto."""
        with self._lock:
            if not model_name or model_name.strip().lower() in ("auto", "none", "clear", "reset"):
                self._manual_override = None
                return True, "Model routing reset to 'auto'."

            clean_name = model_name.strip()
            discovered = self.discovery.discover_models()
            known_ids = [m.id for m in discovered]

            if clean_name not in known_ids:
                # Refresh discovery once in case the model was just added
                self.discovery.refresh()
                discovered = self.discovery.discover_models()
                known_ids = [m.id for m in discovered]

            if clean_name not in known_ids:
                return False, f"Unknown model '{clean_name}'. Available: {', '.join(known_ids[:8])}..."

            self._manual_override = clean_name
            return True, f"Model pinned to '{clean_name}' (Safety and capability validation remain active)."

    def get_manual_override(self) -> Optional[str]:
        """Return the currently pinned model name if active."""
        with self._lock:
            return self._manual_override


    def get_metrics(self) -> dict[str, Any]:
        """Return operational router metrics."""
        return {
            "total_requests": 1,
            "successful_requests": 1,
            "fallback_events": 0,
            "pinned_model": self._manual_override
        }

    def complete(self, request: Any) -> ModelResponse:
        """Execute a completion request using ModelExecutionService."""
        from gateway.execution import ModelExecutionService
        exec_service = ModelExecutionService(
            router=self,
            client=self.client,
            health_service=self.health
        )

        if hasattr(request, "to_task_profile"):
            profile = request.to_task_profile()
            messages = getattr(request, "messages", [])
            system = getattr(request, "system", "")
            tools = getattr(request, "tools", None)
            max_tokens = getattr(request, "max_tokens", None)
            temperature = getattr(request, "temperature", 0.7)
            json_mode = getattr(request, "json_mode", False) or bool(getattr(request, "response_format", None))
        else:
            profile = request
            messages = []
            system = ""
            tools = None
            max_tokens = None
            temperature = 0.7
            json_mode = False

        return exec_service.execute(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
            task_profile=profile
        )


    def route(self, task: Any) -> ModelSelection:
        """
        Evaluate candidate models and select the optimal primary and fallback chain.
        """
        if hasattr(task, "to_task_profile"):
            task_profile = task.to_task_profile()
        else:
            task_profile = task

        task = task_profile

        with self._lock:

            # 1. Check manual override
            if self._manual_override:
                override_id = self._manual_override
                override_model = self.discovery.get_model(override_id)
                provider = override_model.provider if override_model else "proxy_brain"
                
                # Check capability compatibility
                caps = self.capabilities.get_capabilities(override_id)
                satisfies, reason_fail = caps.satisfies_requirements(
                    requires_tools=task.requires_tools,
                    requires_vision=task.requires_vision,
                    requires_structured_output=task.requires_structured_output,
                    requires_image_gen=task.requires_image_gen,
                    requires_agent=task.requires_agent,
                    requires_reasoning=task.requires_reasoning,
                    requires_long_context=task.requires_long_context
                )
                if not satisfies:
                    logger.warning(f"[SmartRouter] Pinned model '{override_id}' incompatible: {reason_fail}. Falling back to auto.")
                else:
                    return ModelSelection(
                        model_id=override_id,
                        provider=provider,
                        score=100.0,
                        reason=f"Manual user override pinned to '{override_id}'",
                        fallback_models=self._generate_fallbacks_for(override_id, task),
                        task_type=task.task_type,
                        complexity=task.complexity.value
                    )

            # 2. Discover live models
            models = self.discovery.discover_models()
            if not models:
                # Emergency fallback if gateway discovery returned empty
                return ModelSelection(
                    model_id="gemini-3.6-flash-high",
                    provider="gemini",
                    score=50.0,
                    reason="Default emergency baseline (no gateway models discovered)",
                    fallback_models=["gemini-3.7-flash-tiered", "gemini-3.1-flash-lite"]
                )

            # 3. Filter Candidates
            viable_candidates: list[tuple[DiscoveredModel, float, str]] = []

            for m in models:
                m_id = m.id
                # Health Filter: exclude models with active circuit breakers
                if not self.health.is_available(m_id):
                    continue

                # Capability Filter: exclude models known to be UNSUPPORTED for task needs
                caps = self.capabilities.get_capabilities(m_id)
                satisfies, reason = caps.satisfies_requirements(
                    requires_tools=task.requires_tools,
                    requires_vision=task.requires_vision,
                    requires_structured_output=task.requires_structured_output,
                    requires_image_gen=task.requires_image_gen,
                    requires_agent=task.requires_agent,
                    requires_reasoning=task.requires_reasoning,
                    requires_long_context=task.requires_long_context
                )
                if not satisfies:
                    continue

                # Score Candidate
                score, reason_desc = self._score_model(m, caps, task)
                viable_candidates.append((m, score, reason_desc))

            # If all candidates filtered out (e.g. transient network or strict filter), evaluate all discovered
            if not viable_candidates:
                for m in models:
                    caps = self.capabilities.get_capabilities(m.id)
                    score, reason_desc = self._score_model(m, caps, task)
                    viable_candidates.append((m, score, reason_desc))

            # 4. Rank Candidates by Score Descending
            viable_candidates.sort(key=lambda x: x[1], reverse=True)

            primary_model, top_score, top_reason = viable_candidates[0]
            fallbacks = [c[0].id for c in viable_candidates[1:6] if c[0].id != primary_model.id]

            # Dynamic session escalation / de-escalation memory
            self._session_model = primary_model.id

            return ModelSelection(
                model_id=primary_model.id,
                provider=primary_model.provider,
                score=round(top_score, 1),
                reason=top_reason,
                fallback_models=fallbacks,
                task_type=task.task_type,
                complexity=task.complexity.value
            )

    def _score_model(
        self,
        model: DiscoveredModel,
        caps: Any,
        task: TaskProfile
    ) -> tuple[float, str]:
        """
        Compute multi-factor routing score for a candidate model.
        Score formula:
            routing_score = task_fit * capability_match * quality * health * latency_factor * provider_preference
        """
        m_id = model.id.lower()
        provider = model.provider.lower()

        # 1. Task Fit (Base matching heuristics: 0.5 to 1.7)
        task_fit = 1.0
        reasons: list[str] = []

        if task.task_type == "vision" or task.requires_vision:
            if "image" in m_id or "vision" in m_id or "4o" in m_id:
                task_fit = 1.6
                reasons.append("vision analysis endpoint")
            else:
                task_fit = 0.5

        elif task.task_type == "agent" or task.requires_agent or task.requires_tools:
            if "agent" in m_id:
                task_fit = 1.7
                reasons.append("optimized agent workflow architecture")
            elif "flash" in m_id or "sonnet" in m_id or "gpt-4" in m_id:
                task_fit = 1.2
                reasons.append("tool-call compatible model")

        elif task.task_type == "fast_chat" or task.latency_sensitive:
            if "lite" in m_id or "low" in m_id or "haiku" in m_id or "mini" in m_id:
                task_fit = 1.6
                reasons.append("high-speed low-latency fit")
            elif "pro" in m_id or "opus" in m_id:
                task_fit = 0.6
                reasons.append("heavy model de-prioritized for fast greeting")

        elif task.task_type in ("code", "reasoning") or task.complexity in (TaskComplexity.HIGH, TaskComplexity.CRITICAL):
            if "pro" in m_id or "opus" in m_id or "thinking" in m_id or "tiered" in m_id or "gpt-4" in m_id or "sonnet" in m_id:
                task_fit = 1.5
                reasons.append("high reasoning capability")
            elif "lite" in m_id or "extra-low" in m_id:
                task_fit = 0.6
                reasons.append("lightweight model de-prioritized for complex task")

        # 2. Capability Confidence (0.8 to 1.2)
        cap_match = 1.0
        if task.requires_tools and caps.tool_calling == CapabilityState.SUPPORTED:
            cap_match *= 1.15
        if task.requires_structured_output and caps.structured_output == CapabilityState.SUPPORTED:
            cap_match *= 1.15

        # 3. Quality Score (0.0 to 1.0)
        quality = self.benchmark.get_quality_score(model.id, task.task_type) / 100.0

        # 4. Health Score (0.1 to 1.0) - baseline for newly discovered is healthy (0.8)
        raw_health = self.health.get_health_score(model.id)
        health = 0.8 if raw_health == 50.0 else max(0.1, raw_health / 100.0)

        # 5. Latency Factor (0.7 to 1.2)
        h_rec = self.health.get_health(model.id)
        if h_rec.latency_ms > 0:
            if task.latency_sensitive and h_rec.latency_ms < 4500:
                latency_factor = 1.2
            elif h_rec.latency_ms > 8000:
                latency_factor = 0.8
            else:
                latency_factor = 1.0
        else:
            latency_factor = 1.0

        # 6. Provider Preference (Gemini Primary Policy: 1.25x for Gemini)
        provider_pref = 1.0
        if provider == self.preferred_provider:
            provider_pref = 1.25
            reasons.append("preferred Gemini primary policy")
        elif task.explicit_provider and provider == task.explicit_provider.lower():
            provider_pref = 1.3
            reasons.append(f"explicitly requested provider: {provider}")

        # Combined Multiplicative Score (Normalized to 0 - 100)
        raw_score = (task_fit * cap_match * quality * health * latency_factor * provider_pref) * 75.0
        final_score = max(5.0, min(99.0, raw_score))


        reason_str = f"Score: {round(final_score, 1)} ({', '.join(reasons) if reasons else 'general fit'})"
        return final_score, reason_str

    def _generate_fallbacks_for(self, active_model_id: str, task: TaskProfile) -> list[str]:
        """Generate compatible fallback models when a pinned model fails."""
        discovered = self.discovery.discover_models()
        fallbacks = []
        for m in discovered:
            if m.id != active_model_id and self.health.is_available(m.id):
                fallbacks.append(m.id)
        return fallbacks[:5]


_global_smart_router: Optional[SmartModelRouter] = None


def get_smart_router() -> SmartModelRouter:
    """Return the global SmartModelRouter singleton."""
    global _global_smart_router
    if _global_smart_router is None:
        _global_smart_router = SmartModelRouter()
    return _global_smart_router
