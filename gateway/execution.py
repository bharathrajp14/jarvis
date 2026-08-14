# gateway/execution.py — Model Execution & Resilient Failover Service
"""
Executes LLM requests with bounded retries, failure-type-specific failovers,
JSON schema validation/repair, and real-time health telemetry accounting.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Generator, Optional, TYPE_CHECKING

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
from gateway.health import ModelHealthService, get_health_service
from router.task_profile import TaskProfile, TaskProfileClassifier

if TYPE_CHECKING:
    from router.smart_router import ModelSelection, SmartModelRouter

logger = logging.getLogger("JARVIS.ModelExecution")


class ModelExecutionService:
    """
    Orchestrates completion execution over dynamic router fallback chains.
    """

    def __init__(
        self,
        router: Optional["SmartModelRouter"] = None,
        client: Optional[ProxyBrainClient] = None,
        health_service: Optional[ModelHealthService] = None,
        max_attempts: int = 3
    ):
        if router is None:
            from router.smart_router import get_smart_router
            self.router = get_smart_router()
        else:
            self.router = router
        self.client = client or get_proxy_brain_client()
        self.health = health_service or get_health_service()
        self.max_attempts = max_attempts

    def execute(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        json_mode: bool = False,
        task_profile: Optional[TaskProfile] = None
    ) -> ModelResponse:
        """
        Execute completion with intelligent, bounded failover across candidates.
        """
        # 1. Profile Task
        profile = task_profile or TaskProfileClassifier.classify(
            messages=messages,
            system=system,
            tools=tools,
            json_mode=json_mode
        )

        # 2. Select Model Chain
        selection: ModelSelection = self.router.route(profile)
        candidate_chain = [selection.model_id] + selection.fallback_models

        last_error: Optional[Exception] = None

        for attempt, model_id in enumerate(candidate_chain[:self.max_attempts], 1):
            logger.info(f"[ModelExecution] Attempt {attempt}/{self.max_attempts} using model '{model_id}' (Reason: {selection.reason})")
            t_start = time.monotonic()

            try:
                resp = self.client.complete(
                    messages=messages,
                    model=model_id,
                    system=system,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode
                )

                latency_ms = (time.monotonic() - t_start) * 1000
                self.health.record_success(model_id, latency_ms)

                # Validate JSON mode if required
                if json_mode and resp.text:
                    try:
                        json.loads(resp.text)
                    except Exception as json_err:
                        logger.warning(f"[ModelExecution] Model '{model_id}' returned invalid JSON: {json_err}. Attempting repair...")
                        # One repair attempt
                        repair_msg = messages + [
                            {"role": "assistant", "content": resp.text},
                            {"role": "user", "content": "The previous output was not valid JSON. Fix it and output only the valid JSON."}
                        ]
                        repair_resp = self.client.complete(
                            messages=repair_msg,
                            model=model_id,
                            system=system,
                            max_tokens=max_tokens,
                            json_mode=True
                        )
                        json.loads(repair_resp.text)
                        return repair_resp

                return resp

            except QuotaExceededError as exc:
                self.health.record_failure(model_id, str(exc), is_quota=True)
                last_error = exc
                logger.warning(f"[ModelExecution] Quota error for '{model_id}'. Failing over to next candidate.")
            except GatewayTimeoutError as exc:
                self.health.record_failure(model_id, str(exc), is_timeout=True)
                last_error = exc
                logger.warning(f"[ModelExecution] Timeout on '{model_id}'. Failing over.")
            except ModelNotFoundError as exc:
                self.health.record_failure(model_id, str(exc))
                last_error = exc
                logger.warning(f"[ModelExecution] Model '{model_id}' not found. Failing over.")
            except GatewayAuthenticationError as exc:
                # Auth failures are fatal, do not cycle endlessly
                self.health.record_failure(model_id, str(exc))
                raise
            except Exception as exc:
                self.health.record_failure(model_id, str(exc))
                last_error = exc
                logger.warning(f"[ModelExecution] Error with '{model_id}': {sanitize_error_msg(str(exc))}. Failing over.")

        # If all candidates exhausted, raise structured failure
        err_msg = f"All {self.max_attempts} model attempts exhausted. Last error: {sanitize_error_msg(str(last_error))}"
        logger.error(f"[ModelExecution] {err_msg}")
        raise ProxyBrainClientError(err_msg)

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        task_profile: Optional[TaskProfile] = None
    ) -> Generator[str, None, None]:
        """Stream chat completion using the optimal routed model."""
        profile = task_profile or TaskProfileClassifier.classify(
            messages=messages,
            system=system,
            tools=tools
        )
        selection = self.router.route(profile)
        yield from self.client.stream(
            messages=messages,
            model=selection.model_id,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature
        )


_global_execution_service: Optional[ModelExecutionService] = None


def get_execution_service() -> ModelExecutionService:
    """Return the global ModelExecutionService singleton."""
    global _global_execution_service
    if _global_execution_service is None:
        _global_execution_service = ModelExecutionService()
    return _global_execution_service
