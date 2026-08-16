# backends/openai_compat.py — JARVIS MK37 OpenAI-Compatible Backend
"""
OpenAI-compatible backend connector for BR Core.
Delegates to the centralized ModelGateway pointing to Proxy Brain (default: http://localhost:8045/v1).
"""
from __future__ import annotations

import logging
import os
from typing import Generator

from .base import BaseBackend
from gateway.model_gateway import ModelGateway, get_model_gateway

logger = logging.getLogger("JARVIS.OpenAI")


class OpenAIBackend(BaseBackend):
    """OpenAI-compatible backend adapter wrapping the centralized ModelGateway."""

    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        self._explicit_model = model or os.environ.get("OPENAI_MODEL", "").strip() or None
        self.model = self._explicit_model or "gemini-3.6-flash-high"
        self._gateway = ModelGateway(base_url=base_url, api_key=api_key)

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def is_local(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return True

    def complete(self, messages: list, system: str = "", tools: list = None, max_tokens: int = None) -> str:
        try:
            resp = self._gateway.complete(
                messages=messages,
                model=self.model,
                system=system,
                tools=tools,
                max_tokens=max_tokens
            )
            return resp.text
        except Exception as e:
            logger.warning("[OpenAI] Completion notice: %s", e)
            return f"ERROR: {e}"

    def stream(self, messages: list, system: str = "", max_tokens: int = None) -> Generator[str, None, None]:
        try:
            yield from self._gateway.stream(
                messages=messages,
                model=self.model,
                system=system,
                max_tokens=max_tokens
            )
        except Exception as e:
            yield f"[OpenAI Stream Error: {e}]"
