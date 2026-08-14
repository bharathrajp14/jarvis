# gateway/capabilities.py — Progressive Model Capability Registry
"""
Inspects, tracks, and registers model capabilities with three explicit states:
  SUPPORTED, UNSUPPORTED, UNKNOWN.

Decouples model names from capabilities. Name substrings are treated ONLY as initial
provisional hints; true capabilities are verified progressively via lazy probes on demand.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("JARVIS.ModelCapabilities")


class CapabilityState(str, Enum):
    """Explicit 3-state representation of capability status."""
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"

    def is_supported(self) -> bool:
        return self == CapabilityState.SUPPORTED

    def is_verified(self) -> bool:
        return self in (CapabilityState.SUPPORTED, CapabilityState.UNSUPPORTED)


@dataclass
class ModelCapabilities:
    """9-dimensional capability profile for an LLM."""
    chat: CapabilityState = CapabilityState.SUPPORTED
    streaming: CapabilityState = CapabilityState.SUPPORTED
    structured_output: CapabilityState = CapabilityState.UNKNOWN
    tool_calling: CapabilityState = CapabilityState.UNKNOWN
    vision: CapabilityState = CapabilityState.UNKNOWN
    image_generation: CapabilityState = CapabilityState.UNKNOWN
    reasoning: CapabilityState = CapabilityState.UNKNOWN
    agentic: CapabilityState = CapabilityState.UNKNOWN
    large_context: CapabilityState = CapabilityState.UNKNOWN

    # Verified performance metrics
    verified_context_window: int = 8192
    last_verified_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chat": self.chat.value,
            "streaming": self.streaming.value,
            "structured_output": self.structured_output.value,
            "tool_calling": self.tool_calling.value,
            "vision": self.vision.value,
            "image_generation": self.image_generation.value,
            "reasoning": self.reasoning.value,
            "agentic": self.agentic.value,
            "large_context": self.large_context.value,
            "verified_context_window": self.verified_context_window,
            "last_verified_at": self.last_verified_at,
        }

    def satisfies_requirements(
        self,
        requires_tools: bool = False,
        requires_vision: bool = False,
        requires_structured_output: bool = False,
        requires_image_gen: bool = False,
        requires_agent: bool = False,
        requires_reasoning: bool = False,
        requires_long_context: bool = False
    ) -> tuple[bool, str]:
        """
        Check if capabilities satisfy all required dimensions.
        UNKNOWN is NOT treated as supported when strict verification is required.
        """
        if requires_tools and self.tool_calling == CapabilityState.UNSUPPORTED:
            return False, "tool_calling unsupported"
        if requires_vision and self.vision == CapabilityState.UNSUPPORTED:
            return False, "vision unsupported"
        if requires_structured_output and self.structured_output == CapabilityState.UNSUPPORTED:
            return False, "structured_output unsupported"
        if requires_image_gen and self.image_generation == CapabilityState.UNSUPPORTED:
            return False, "image_generation unsupported"
        if requires_agent and self.agentic == CapabilityState.UNSUPPORTED:
            return False, "agentic unsupported"
        if requires_reasoning and self.reasoning == CapabilityState.UNSUPPORTED:
            return False, "reasoning unsupported"

        return True, "requirements satisfied"


class ModelCapabilityRegistry:
    """
    Maintains progressive capability profiles for all discovered models.
    """

    def __init__(self):
        self._profiles: dict[str, ModelCapabilities] = {}
        self._lock = threading.RLock()

    def get_capabilities(self, model_id: str) -> ModelCapabilities:
        """Retrieve or initialize capability profile for a model."""
        with self._lock:
            if model_id not in self._profiles:
                self._profiles[model_id] = self._generate_provisional_profile(model_id)
            return self._profiles[model_id]

    def set_capability(
        self,
        model_id: str,
        capability: str,
        state: CapabilityState
    ) -> None:
        """Update a specific capability after empirical verification."""
        with self._lock:
            profile = self.get_capabilities(model_id)
            if hasattr(profile, capability):
                setattr(profile, capability, state)
                logger.debug(f"[Capabilities] Updated {model_id}.{capability} = {state.value}")

    def update_verification(
        self,
        model_id: str,
        tool_calling: Optional[CapabilityState] = None,
        structured_output: Optional[CapabilityState] = None,
        vision: Optional[CapabilityState] = None,
        image_generation: Optional[CapabilityState] = None,
        reasoning: Optional[CapabilityState] = None,
        agentic: Optional[CapabilityState] = None
    ) -> None:
        """Bulk update verified capabilities after benchmark or live execution."""
        with self._lock:
            profile = self.get_capabilities(model_id)
            if tool_calling is not None:
                profile.tool_calling = tool_calling
            if structured_output is not None:
                profile.structured_output = structured_output
            if vision is not None:
                profile.vision = vision
            if image_generation is not None:
                profile.image_generation = image_generation
            if reasoning is not None:
                profile.reasoning = reasoning
            if agentic is not None:
                profile.agentic = agentic

    def _generate_provisional_profile(self, model_id: str) -> ModelCapabilities:
        """
        Generate an initial capability profile.
        Naming heuristics provide provisional hints only; critical vectors default to UNKNOWN.
        """
        m_id = model_id.lower()
        cap = ModelCapabilities()

        # Image generation endpoint detection
        if "image" in m_id and ("1x1" in m_id or "16x9" in m_id or "2k" in m_id or "4k" in m_id):
            cap.image_generation = CapabilityState.UNKNOWN
            cap.chat = CapabilityState.UNSUPPORTED
            return cap

        # Vision hint
        if "image" in m_id or "vision" in m_id or "4o" in m_id:
            cap.vision = CapabilityState.UNKNOWN  # Provisional hint, verified via lazy probe

        # Tool calling / Agent hint
        if "agent" in m_id or "flash" in m_id or "pro" in m_id or "sonnet" in m_id or "gpt-4" in m_id:
            cap.tool_calling = CapabilityState.UNKNOWN
            cap.structured_output = CapabilityState.UNKNOWN

        # Deep reasoning hint
        if "thinking" in m_id or "pro" in m_id or "opus" in m_id or "tiered" in m_id:
            cap.reasoning = CapabilityState.UNKNOWN

        return cap


_global_capability_registry: Optional[ModelCapabilityRegistry] = None


def get_capability_registry() -> ModelCapabilityRegistry:
    """Return the global ModelCapabilityRegistry singleton."""
    global _global_capability_registry
    if _global_capability_registry is None:
        _global_capability_registry = ModelCapabilityRegistry()
    return _global_capability_registry
