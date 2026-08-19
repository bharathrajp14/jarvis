# backends/nvidia.py — JARVIS MK37 NVIDIA NIM Backend
"""
NVIDIA NIM backend connector for BR Core.
Uses the OpenAI SDK pointed at NVIDIA's API endpoint.
"""

from __future__ import annotations

import logging
import os
from typing import Generator

from .base import BaseBackend

logger = logging.getLogger(__name__)


class NvidiaBackend(BaseBackend):
    """NVIDIA NIM backend for GPU-accelerated inference."""

    def __init__(self, model: str = None, api_key: str = None):
        try:
            from brjarvis.config.models import get_model

            default_model = get_model("nvidia") or "meta/llama3-70b-instruct"
        except Exception:
            default_model = "meta/llama3-70b-instruct"

        self.model = model or default_model
        self.client = None

        _api_key = api_key or os.environ.get("NVIDIA_API_KEY", "").strip()
        if _api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=_api_key,
                )
                logger.info(f"[NVIDIA] [OK] Using model: {self.model}")
            except ImportError:
                logger.info("[NVIDIA] Warning: openai package is not installed.")

    @property
    def name(self) -> str:
        return "NVIDIA"

    @property
    def model_name(self) -> str:
        return self.model

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "NVIDIA client is not initialized. "
                "Ensure NVIDIA_API_KEY is configured in your environment or .env, "
                "and the 'openai' pip package is installed."
            )

    def _get_extra_body(self) -> dict:
        """Enable thinking for supported models."""
        if "deepseek" in self.model or "llama" in self.model:
            return {"chat_template_kwargs": {"enable_thinking": True, "clear_thinking": False}}
        return {}

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        try:
            self._ensure_client()

            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            extra_body = self._get_extra_body()
            kwargs = {
                "model": self.model,
                "messages": full_messages,
                "temperature": 1,
                "top_p": 1,
                "max_tokens": 8192,
            }
            if extra_body:
                kwargs["extra_body"] = extra_body

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"[NVIDIA] Error: {e}")
            raise

    def stream(self, messages: list, system: str = "") -> Generator[str, None, None]:
        try:
            self._ensure_client()

            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            extra_body = self._get_extra_body()
            kwargs = {
                "model": self.model,
                "messages": full_messages,
                "temperature": 1,
                "top_p": 1,
                "max_tokens": 8192,
                "stream": True,
            }
            if extra_body:
                kwargs["extra_body"] = extra_body

            stream_res = self.client.chat.completions.create(**kwargs)
            for chunk in stream_res:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[NVIDIA Stream Error: {e}]"
