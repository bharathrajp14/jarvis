# backends/mistral.py — JARVIS MK37 Mistral Backend
"""
Mistral backend connector for BR Core.
Uses the OpenAI SDK pointed at Mistral's API endpoint.
"""

from __future__ import annotations

import logging
import os
from typing import Generator

from .base import BaseBackend

logger = logging.getLogger(__name__)


class MistralBackend(BaseBackend):
    """Mistral AI backend via OpenAI-compatible SDK."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            from brjarvis.config.models import get_model

            default_model = get_model("mistral") or "mistral-large-latest"
        except Exception:
            default_model = "mistral-large-latest"

        self.model = model or default_model
        self.client = None

        _api_key = api_key or os.environ.get("MISTRAL_API_KEY", "").strip()
        if _api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=_api_key, base_url="https://api.mistral.ai/v1")
                logger.info(f"[Mistral] [OK] Using model: {self.model}")
            except ImportError:
                logger.info("[Mistral] Warning: openai package is not installed.")

    @property
    def name(self) -> str:
        return "Mistral"

    @property
    def model_name(self) -> str:
        return self.model

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "Mistral client is not initialized. "
                "Ensure MISTRAL_API_KEY is configured in your environment or .env, "
                "and the 'openai' pip package is installed."
            )

    def complete(self, messages: list[dict], system: str = "", tools: list | None = None) -> str:
        try:
            self._ensure_client()
            assert self.client is not None

            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            kwargs = {
                "model": self.model,
                "messages": full_messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"[Mistral] Error: {e}")
            raise

    def stream(self, messages: list[dict], system: str = "") -> Generator[str, None, None]:
        try:
            self._ensure_client()
            assert self.client is not None

            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            stream_res = self.client.chat.completions.create(model=self.model, messages=full_messages, stream=True)
            for chunk in stream_res:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            yield f"\n[Mistral Stream Error: {e}]"
