# gateway/__init__.py — BR JARVIS Model Gateway & Dynamic Intelligence Package
"""
Unified gateway client, discovery, health, capability, benchmark, and execution services.
"""
from __future__ import annotations

from gateway.client import (
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
from gateway.discovery import (
    DiscoveredModel,
    ModelDiscoveryService,
    get_discovery_service,
)
from gateway.capabilities import (
    CapabilityState,
    ModelCapabilities,
    ModelCapabilityRegistry,
    get_capability_registry,
)
from gateway.health import (
    HealthState,
    ModelHealthRecord,
    ModelHealthService,
    get_health_service,
)
from gateway.benchmark import (
    BenchmarkScore,
    BenchmarkTaskType,
    ModelBenchmarkService,
    get_benchmark_service,
)
from gateway.execution import (
    ModelExecutionService,
    get_execution_service,
)
from gateway.model_gateway import (
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
