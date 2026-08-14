# gateway/models_registry.py — Typed Model Registry & Capability Mapping for BR JARVIS
"""
Typed Model Registry defining model capabilities, tiers, performance profiles,
and task mappings for the Proxy Brain gateway.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger("JARVIS.ModelRegistry")


class TaskCapability(str, Enum):
    CHAT            = "chat"
    FAST_CHAT       = "fast_chat"
    REASONING       = "reasoning"
    DEEP_REASONING  = "deep_reasoning"
    PLANNING        = "planning"
    AGENT           = "agent"
    CODE            = "code"
    CODE_REVIEW     = "code_review"
    TOOL_SELECTION  = "tool_selection"
    VISION          = "vision"
    IMAGE           = "image"
    SUMMARIZATION   = "summarization"
    CLASSIFICATION  = "classification"
    EXTRACTION      = "extraction"
    LONG_CONTEXT    = "long_context"
    LOW_LATENCY     = "low_latency"
    FALLBACK        = "fallback"


class ModelTier(str, Enum):
    LITE           = "lite"            # Fast, low latency, low resource
    BALANCED       = "balanced"        # General purpose, strong everyday chat
    PRO            = "pro"             # High reasoning, complex code/architecture
    HIGH_REASONING = "high_reasoning"  # Multi-step deep thinking and analysis


@dataclass(frozen=True)
class ModelSpec:
    """Detailed specification and capability profile of an AI model."""
    id: str
    provider: str                      # "google", "anthropic", "openai", "meta"
    family: str                        # "gemini", "claude", "gpt", "llama"
    capabilities: frozenset[TaskCapability]
    tier: ModelTier
    speed: str                         # "fast", "medium", "slow"
    context_class: str                 # "standard", "large", "huge"
    tool_use: bool = True
    vision: bool = False
    image_generation: bool = False
    thinking: bool = False
    preferred_for: list[str] = field(default_factory=list)

    def matches_capability(self, cap: TaskCapability) -> bool:
        return cap in self.capabilities


# ── Canonical Proxy Brain Model Catalog ─────────────────────────────────────

_CANONICAL_MODELS: list[ModelSpec] = [
    # Gemini Tiered & High Flash Models
    ModelSpec(
        id="gemini-3.7-flash-tiered",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.REASONING, TaskCapability.PLANNING,
            TaskCapability.AGENT, TaskCapability.CODE, TaskCapability.TOOL_SELECTION,
            TaskCapability.LONG_CONTEXT, TaskCapability.FALLBACK
        }),
        tier=ModelTier.PRO,
        speed="fast",
        context_class="huge",
        tool_use=True,
        thinking=True,
        preferred_for=["planning", "agentic_tasks", "complex_reasoning", "code"]
    ),
    ModelSpec(
        id="gemini-3.6-flash-high",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.REASONING, TaskCapability.PLANNING,
            TaskCapability.AGENT, TaskCapability.CODE, TaskCapability.TOOL_SELECTION,
            TaskCapability.LONG_CONTEXT, TaskCapability.SUMMARIZATION, TaskCapability.FALLBACK
        }),
        tier=ModelTier.BALANCED,
        speed="fast",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["general_conversation", "code_generation", "fast_reasoning"]
    ),
    ModelSpec(
        id="gemini-3.6-flash-medium",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.PLANNING, TaskCapability.AGENT,
            TaskCapability.TOOL_SELECTION, TaskCapability.SUMMARIZATION
        }),
        tier=ModelTier.BALANCED,
        speed="fast",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["standard_chat", "summarization", "agent_workflows"]
    ),
    ModelSpec(
        id="gemini-3.6-flash-low",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.FAST_CHAT, TaskCapability.LOW_LATENCY, TaskCapability.SUMMARIZATION,
            TaskCapability.CLASSIFICATION, TaskCapability.EXTRACTION
        }),
        tier=ModelTier.LITE,
        speed="fast",
        context_class="standard",
        tool_use=True,
        thinking=False,
        preferred_for=["quick_status", "lightweight_extraction", "classification"]
    ),
    ModelSpec(
        id="gemini-3.6-flash-tiered",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.REASONING, TaskCapability.PLANNING,
            TaskCapability.AGENT, TaskCapability.CODE, TaskCapability.TOOL_SELECTION
        }),
        tier=ModelTier.BALANCED,
        speed="fast",
        context_class="large",
        tool_use=True,
        thinking=True,
        preferred_for=["adaptive_chat", "agent_tasks"]
    ),

    # Gemini Pro Reasoning Models
    ModelSpec(
        id="gemini-3.1-pro-high",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.REASONING, TaskCapability.DEEP_REASONING, TaskCapability.CODE,
            TaskCapability.CODE_REVIEW, TaskCapability.PLANNING, TaskCapability.LONG_CONTEXT
        }),
        tier=ModelTier.HIGH_REASONING,
        speed="medium",
        context_class="huge",
        tool_use=True,
        thinking=True,
        preferred_for=["complex_reasoning", "security_audits", "architecture_design", "deep_code_analysis"]
    ),
    ModelSpec(
        id="gemini-3.1-pro-low",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.REASONING, TaskCapability.CODE, TaskCapability.PLANNING
        }),
        tier=ModelTier.PRO,
        speed="medium",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["code_tasks", "moderate_reasoning"]
    ),

    # Gemini Lite & Vision Specialized Models
    ModelSpec(
        id="gemini-3.1-flash-lite",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.FAST_CHAT, TaskCapability.LOW_LATENCY, TaskCapability.CLASSIFICATION,
            TaskCapability.EXTRACTION, TaskCapability.SUMMARIZATION
        }),
        tier=ModelTier.LITE,
        speed="fast",
        context_class="standard",
        tool_use=True,
        thinking=False,
        preferred_for=["autocomplete", "low_latency_responses", "tagging", "extraction"]
    ),
    ModelSpec(
        id="gemini-3.1-flash-image",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.VISION, TaskCapability.IMAGE, TaskCapability.CHAT
        }),
        tier=ModelTier.BALANCED,
        speed="medium",
        context_class="large",
        tool_use=True,
        vision=True,
        preferred_for=["screen_analysis", "ocr", "image_inspection", "ui_scanning"]
    ),

    # Gemini Agent Models
    ModelSpec(
        id="gemini-3-flash-agent",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.AGENT, TaskCapability.PLANNING, TaskCapability.TOOL_SELECTION,
            TaskCapability.CHAT, TaskCapability.CODE
        }),
        tier=ModelTier.BALANCED,
        speed="fast",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["multi_step_agent_tasks", "browser_automation", "desktop_control"]
    ),
    ModelSpec(
        id="gemini-pro-agent",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.AGENT, TaskCapability.PLANNING, TaskCapability.TOOL_SELECTION,
            TaskCapability.REASONING, TaskCapability.CODE
        }),
        tier=ModelTier.PRO,
        speed="medium",
        context_class="huge",
        tool_use=True,
        thinking=True,
        preferred_for=["complex_autonomous_workflows", "dev_agent_pipelines"]
    ),
    ModelSpec(
        id="gemini-3-flash",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.FAST_CHAT, TaskCapability.SUMMARIZATION,
            TaskCapability.TOOL_SELECTION
        }),
        tier=ModelTier.BALANCED,
        speed="fast",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["general_chat", "quick_answers"]
    ),

    # Gemini 2.5 Generation Models
    ModelSpec(
        id="gemini-2.5-pro",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.REASONING, TaskCapability.CODE, TaskCapability.PLANNING,
            TaskCapability.LONG_CONTEXT
        }),
        tier=ModelTier.PRO,
        speed="medium",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["fallback_reasoning", "long_context_analysis"]
    ),
    ModelSpec(
        id="gemini-2.5-flash",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.FAST_CHAT, TaskCapability.SUMMARIZATION
        }),
        tier=ModelTier.BALANCED,
        speed="fast",
        context_class="standard",
        tool_use=True,
        thinking=False,
        preferred_for=["fallback_chat"]
    ),
    ModelSpec(
        id="gemini-2.5-flash-lite",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.FAST_CHAT, TaskCapability.LOW_LATENCY, TaskCapability.CLASSIFICATION
        }),
        tier=ModelTier.LITE,
        speed="fast",
        context_class="standard",
        tool_use=True,
        thinking=False,
        preferred_for=["voice_replies", "fast_classification"]
    ),
    ModelSpec(
        id="gemini-2.5-flash-thinking",
        provider="google",
        family="gemini",
        capabilities=frozenset({
            TaskCapability.REASONING, TaskCapability.PLANNING, TaskCapability.CODE
        }),
        tier=ModelTier.PRO,
        speed="medium",
        context_class="large",
        tool_use=True,
        thinking=True,
        preferred_for=["step_by_step_reasoning"]
    ),

    # Claude Models on Proxy Brain
    ModelSpec(
        id="claude-opus-4-6-thinking",
        provider="anthropic",
        family="claude",
        capabilities=frozenset({
            TaskCapability.DEEP_REASONING, TaskCapability.REASONING, TaskCapability.CODE_REVIEW,
            TaskCapability.PLANNING, TaskCapability.LONG_CONTEXT
        }),
        tier=ModelTier.HIGH_REASONING,
        speed="slow",
        context_class="huge",
        tool_use=True,
        thinking=True,
        preferred_for=["deep_creative_writing", "philosophical_analysis", "critical_architecture_review"]
    ),
    ModelSpec(
        id="claude-sonnet-4-6",
        provider="anthropic",
        family="claude",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.REASONING, TaskCapability.CODE,
            TaskCapability.CODE_REVIEW, TaskCapability.TOOL_SELECTION
        }),
        tier=ModelTier.PRO,
        speed="medium",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["technical_writing", "code_refactoring", "analysis"]
    ),

    # GPT Models on Proxy Brain
    ModelSpec(
        id="gpt-oss-120b-medium",
        provider="openai",
        family="gpt",
        capabilities=frozenset({
            TaskCapability.CHAT, TaskCapability.REASONING, TaskCapability.CODE,
            TaskCapability.SUMMARIZATION
        }),
        tier=ModelTier.BALANCED,
        speed="medium",
        context_class="large",
        tool_use=True,
        thinking=False,
        preferred_for=["alternative_completions", "cross_verification"]
    ),
]


class ModelRegistry:
    """Central typed repository of model specifications and capabilities."""

    def __init__(self, custom_specs: Optional[list[ModelSpec]] = None):
        self._specs: dict[str, ModelSpec] = {}
        for spec in (custom_specs or _CANONICAL_MODELS):
            self._specs[spec.id.lower()] = spec

    def get(self, model_id: str) -> Optional[ModelSpec]:
        """Look up a model by its identifier."""
        if not model_id:
            return None
        return self._specs.get(model_id.strip().lower())

    def list_all(self) -> list[ModelSpec]:
        """Return all registered model specifications."""
        return list(self._specs.values())

    def list_ids(self) -> list[str]:
        """Return list of all registered model IDs."""
        return list(self._specs.keys())

    def find_by_capability(self, capability: TaskCapability) -> list[ModelSpec]:
        """Find all models providing the given capability."""
        return [m for m in self._specs.values() if m.matches_capability(capability)]

    def get_best_for_capability(
        self,
        capability: TaskCapability,
        tier_preference: Optional[ModelTier] = None,
        available_subset: Optional[set[str]] = None
    ) -> Optional[ModelSpec]:
        """Find the best matching model for a capability, optionally filtering to available models."""
        candidates = self.find_by_capability(capability)
        if available_subset is not None:
            norm_subset = {s.lower() for s in available_subset}
            candidates = [c for c in candidates if c.id.lower() in norm_subset]

        if not candidates:
            return None

        # Prioritize Gemini family by default
        gemini_candidates = [c for c in candidates if c.family == "gemini"]
        pool = gemini_candidates if gemini_candidates else candidates

        if tier_preference:
            tier_matches = [c for c in pool if c.tier == tier_preference]
            if tier_matches:
                return tier_matches[0]

        return pool[0]

    def register(self, spec: ModelSpec) -> None:
        """Register or update a model specification."""
        self._specs[spec.id.lower()] = spec


_global_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """Return the global model registry singleton."""
    return _global_registry
