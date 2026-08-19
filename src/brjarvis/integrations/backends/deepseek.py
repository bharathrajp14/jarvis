# backends/deepseek.py — JARVIS MK37 DeepSeek & OpenRouter AI Backend Connector
"""
DeepSeek and OpenRouter backend connector for BR Core.
Supports DeepSeek-R1 reasoning models, DeepSeek-V3, and OpenRouter unified proxying.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Generator, List

from .base import BaseBackend

logger = logging.getLogger("JARVIS.DeepSeek")


class DeepSeekBackend(BaseBackend):
    """DeepSeek & OpenRouter high-performance AI backend connector."""

    def __init__(self, model: str = None, api_key: str = None):
        _api_key = (
            api_key
            or os.environ.get("DEEPSEEK_API_KEY", "").strip()
            or os.environ.get("OPENROUTER_API_KEY", "").strip()
        )
        if not _api_key:
            try:
                from brjarvis.core.config import get_config

                _api_key = (get_config().secrets.deepseek_api_key or "").strip()
            except Exception:
                pass
        if not _api_key:
            try:
                from brjarvis.core.paths import paths

                cfg_file = paths.CONFIG_ROOT / "api_keys.json"
                if cfg_file.exists():
                    import json

                    data = json.loads(cfg_file.read_text(encoding="utf-8"))
                    for k, v in data.items():
                        if str(k).lower().strip() in ("deepseek_api_key", "openrouter_api_key") and str(v).strip():
                            _api_key = str(v).strip()
                            break
            except Exception:
                pass

        is_openrouter = not os.environ.get("DEEPSEEK_API_KEY") and bool(os.environ.get("OPENROUTER_API_KEY"))
        self.base_url = "https://openrouter.ai/api/v1" if is_openrouter else "https://api.deepseek.com/v1"

        default_model = "deepseek/deepseek-r1" if is_openrouter else "deepseek-reasoner"
        self.model = model or default_model
        self.client = None

        if _api_key:
            try:
                import openai

                self.client = openai.OpenAI(api_key=_api_key, base_url=self.base_url)
                logger.info("Initialized backend with model: %s on base_url: %s", self.model, self.base_url)
            except ImportError:
                logger.warning("openai client library is not installed.")

    @property
    def name(self) -> str:
        return "DeepSeek"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def available(self) -> bool:
        if os.environ.get("JARVIS_DISABLE_DEEPSEEK", "").strip().lower() in {"1", "true", "yes", "on"}:
            return False
        return self.client is not None

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "DeepSeek client is not initialized. "
                "Ensure DEEPSEEK_API_KEY or OPENROUTER_API_KEY is configured in your environment or .env file."
            )

    def _format_messages(self, messages: List[Dict[str, Any]], system: str = "") -> List[Dict[str, Any]]:
        formatted = []
        if system:
            formatted.append({"role": "system", "content": system})
        for msg in messages:
            formatted.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        return formatted

    def complete(self, messages: List[Dict[str, Any]], system: str = "", tools: List[Any] | None = None) -> str:
        try:
            self._ensure_client()
            formatted = self._format_messages(messages, system)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"[DeepSeek] Error during completion: {e}")
            raise

    def stream(self, messages: List[Dict[str, Any]], system: str = "") -> Generator[str, None, None]:
        try:
            self._ensure_client()
            formatted = self._format_messages(messages, system)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted,
                temperature=0.3,
                stream=True,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[DeepSeek Stream Error: {e}]"
