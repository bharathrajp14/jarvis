# gateway/__init__.py — BR JARVIS Model Gateway & Dynamic Intelligence Package
"""
Unified gateway client, discovery, health, capability, benchmark, and execution services.
"""
from __future__ import annotations

import sys
_mod = sys.modules.get(__name__)
if _mod:
    sys.modules["gateway"] = _mod
    sys.modules["brjarvis.gateway"] = _mod

from .client import (
    GatewayAuthenticationError,
    GatewayTimeoutError,
    GatewayUnavailableError,
    MalformedResponseError,
    ModelNotFoundError,
    ModelResponse,
    ProxyBrainClient,
    ProxyBrainClientError,
    QuotaExceededError,
    get_proxy_brain_client,
    sanitize_error_msg,
)
from .discovery import (
    DiscoveredModel,
    ModelDiscoveryService,
    get_discovery_service,
)
from .capabilities import (
    CapabilityState,
    ModelCapabilities,
    ModelCapabilityRegistry,
    get_capability_registry,
)
from .health import (
    HealthState,
    ModelHealthRecord,
    ModelHealthService,
    get_health_service,
)
from .benchmark import (
    BenchmarkScore,
    BenchmarkTaskType,
    ModelBenchmarkService,
    get_benchmark_service,
)
from .execution import (
    ModelExecutionService,
    get_execution_service,
)
from .model_gateway import (
    ModelGateway,
    get_model_gateway,
)

__all__ = [
    "ProxyBrainClient",
    "ProxyBrainClientError",
    "GatewayUnavailableError",
    "ModelNotFoundError",
    "QuotaExceededError",
    "GatewayTimeoutError",
    "GatewayAuthenticationError",
    "MalformedResponseError",
    "ModelResponse",
    "get_proxy_brain_client",
    "sanitize_error_msg",
    "DiscoveredModel",
    "ModelDiscoveryService",
    "get_discovery_service",
    "CapabilityState",
    "ModelCapabilities",
    "ModelCapabilityRegistry",
    "get_capability_registry",
    "HealthState",
    "ModelHealthRecord",
    "ModelHealthService",
    "get_health_service",
    "BenchmarkScore",
    "BenchmarkTaskType",
    "ModelBenchmarkService",
    "get_benchmark_service",
    "ModelExecutionService",
    "get_execution_service",
    "ModelGateway",
    "get_model_gateway",
]
