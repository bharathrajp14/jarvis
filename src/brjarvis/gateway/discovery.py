# gateway/discovery.py — Dynamic Model Discovery Service
"""
Discovers available models from the local Proxy Brain gateway via GET /v1/models.
Maintains a thread-safe, TTL-cached inventory of DiscoveredModel entities.
Supports startup discovery, periodic background sync, manual refresh (/model refresh),
and on-routing-failure refresh.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

from .client import ProxyBrainClient, get_proxy_brain_client, sanitize_error_msg

logger = logging.getLogger("JARVIS.ModelDiscovery")


@dataclass
class DiscoveredModel:
    """Represents a model dynamically discovered from the gateway."""

    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = ""
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    discovered_at: float = field(default_factory=time.time)

    @property
    def provider(self) -> str:
        """Heuristic provider extraction from model id or owner."""
        m_id = self.id.lower()
        if "gemini" in m_id or "google" in self.owned_by.lower():
            return "gemini"
        elif "claude" in m_id or "anthropic" in self.owned_by.lower():
            return "anthropic"
        elif "gpt" in m_id or "openai" in self.owned_by.lower():
            return "openai"
        elif "ollama" in m_id or "local" in self.owned_by.lower():
            return "local"
        return "proxy_brain"


class ModelDiscoveryService:
    """
    Manages live model discovery from Proxy Brain.
    """

    def __init__(self, client: Optional[ProxyBrainClient] = None, cache_ttl_seconds: float = 300.0):
        self.client = client or get_proxy_brain_client()
        self.cache_ttl = cache_ttl_seconds
        self._models: dict[str, DiscoveredModel] = {}
        self._last_discovery_time: float = 0.0
        self._lock = threading.RLock()

    def discover_models(self, force_refresh: bool = False) -> list[DiscoveredModel]:
        """
        Retrieve available models from Proxy Brain gateway.
        Uses TTL cache unless force_refresh is True or cache is empty/expired.
        """
        with self._lock:
            now = time.time()
            if not force_refresh and self._models and (now - self._last_discovery_time < self.cache_ttl):
                return list(self._models.values())

            url = f"{self.client.base_url}/models"
            headers = {"Authorization": f"Bearer {self.client.api_key}", "Content-Type": "application/json"}

            try:
                r = requests.get(url, headers=headers, timeout=self.client.timeout)
                if r.status_code == 200:
                    data = r.json()
                    model_entries = data.get("data", []) if isinstance(data, dict) else []
                    new_models: dict[str, DiscoveredModel] = {}

                    for item in model_entries:
                        if isinstance(item, dict) and item.get("id"):
                            m_id = str(item["id"]).strip()
                            new_models[m_id] = DiscoveredModel(
                                id=m_id,
                                object=item.get("object", "model"),
                                created=int(item.get("created", 0) or 0),
                                owned_by=str(item.get("owned_by", "")),
                                raw_metadata=item,
                                discovered_at=now,
                            )

                    if new_models:
                        self._models = new_models
                        self._last_discovery_time = now
                        logger.info(f"[Discovery] Discovered {len(self._models)} live models from {url}")
                        return list(self._models.values())
                else:
                    logger.warning(
                        f"[Discovery] GET /v1/models returned HTTP {r.status_code}: {sanitize_error_msg(r.text[:100])}"
                    )
            except Exception as exc:
                logger.warning(f"[Discovery] Failed to reach /v1/models: {sanitize_error_msg(str(exc))}")

            # Return whatever was previously cached if network call failed
            return list(self._models.values())

    def get_model(self, model_id: str) -> Optional[DiscoveredModel]:
        """Retrieve metadata for a specific model ID."""
        with self._lock:
            if not self._models:
                self.discover_models()
            return self._models.get(model_id)

    def is_model_discovered(self, model_id: str) -> bool:
        """Check whether a model exists in the discovered inventory."""
        with self._lock:
            if not self._models:
                self.discover_models()
            return model_id in self._models

    def refresh(self) -> int:
        """Explicitly refresh the model inventory and return count of discovered models."""
        models = self.discover_models(force_refresh=True)
        return len(models)

    def get_inventory_summary(self) -> dict[str, Any]:
        """Return diagnostic summary of discovered models."""
        with self._lock:
            models = self.discover_models()
            by_provider: dict[str, list[str]] = {}
            for m in models:
                by_provider.setdefault(m.provider, []).append(m.id)
            return {
                "total_models": len(models),
                "last_discovery_time": self._last_discovery_time,
                "providers": {p: len(m_list) for p, m_list in by_provider.items()},
                "model_ids": [m.id for m in models],
            }


_global_discovery_service: Optional[ModelDiscoveryService] = None


def get_discovery_service() -> ModelDiscoveryService:
    """Return the global ModelDiscoveryService singleton."""
    global _global_discovery_service
    if _global_discovery_service is None:
        _global_discovery_service = ModelDiscoveryService()
    return _global_discovery_service
