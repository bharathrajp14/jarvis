# backends/ollama.py — JARVIS MK37 Ollama (Local LLM) Backend
"""
Ollama backend for local/private inference.
Safe initialization, standardized error handling, JSON schema mode, and text streaming.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Generator, List, Optional

import requests

from .base import BaseBackend

logger = logging.getLogger("JARVIS.OllamaBackend")


class OllamaBackend(BaseBackend):
    """Local Ollama backend for privacy-sensitive tasks and offline inference."""

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None):
        try:
            from brjarvis.config.models import get_model

            default_model = get_model("ollama") or "llama3"
        except Exception:
            default_model = "llama3"

        self.model = model or default_model
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def is_local(self) -> bool:
        """Ollama is an entirely local on-premise model."""
        return True

    def ping(self, timeout: float = 2.0) -> bool:
        """Fast connectivity check — GET /api/tags with short timeout."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self, timeout: float = 3.0) -> List[str]:
        """List locally pulled models on the Ollama instance."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                return [m.get("name", "") for m in data.get("models", [])]
            return []
        except Exception as e:
            logger.debug("[Ollama] Could not list models: %s", e)
            return []

    def complete(
        self,
        messages: list,
        system: str = "",
        tools: Optional[list] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        try:
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": full_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }
            if json_mode:
                payload["format"] = "json"

            r = requests.post(f"{self.host}/api/chat", json=payload, timeout=60)
            if r.status_code != 200:
                raise ValueError(f"Ollama HTTP error {r.status_code}: {r.text}")

            data = r.json()
            if "error" in data:
                raise ValueError(f"Ollama runtime error: {data['error']}")

            return data["message"]["content"]
        except Exception as e:
            logger.warning("[Ollama] Error: %s", e)
            raise

    def stream(
        self,
        messages: list,
        system: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        try:
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": full_messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                },
            }
            r = requests.post(f"{self.host}/api/chat", json=payload, stream=True, timeout=120)
            if r.status_code != 200:
                yield f"Ollama HTTP error {r.status_code}"
                return

            for line in r.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    if "error" in data:
                        yield f"\n[Ollama Stream Error: {data['error']}]"
                        return
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]
        except Exception as e:
            yield f"\n[Ollama Stream Error: {e}]"
