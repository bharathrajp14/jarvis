# backends/ollama.py — JARVIS MK37 Ollama (Local LLM) Backend
"""
Ollama backend for local/private inference.
Safe initialization, standardized error handling, and text streaming.
"""
from __future__ import annotations

import logging
import json
import os
from typing import Generator

import requests

from backends.base import BaseBackend

logger = logging.getLogger(__name__)


class OllamaBackend(BaseBackend):
    """Local Ollama backend for privacy-sensitive tasks."""

    def __init__(self, model: str = None, host: str = None):
        try:
            from config.models import get_model
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

    def ping(self, timeout: float = 2.0) -> bool:
        """Fast connectivity check — GET /api/tags with short timeout."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        try:
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            payload = {
                "model": self.model,
                "messages": full_messages,
                "stream": False,
            }
            r = requests.post(f"{self.host}/api/chat", json=payload, timeout=60)
            if r.status_code != 200:
                raise ValueError(f"Ollama HTTP error {r.status_code}: {r.text}")

            data = r.json()
            if "error" in data:
                raise ValueError(f"Ollama runtime error: {data['error']}")

            return data["message"]["content"]
        except Exception as e:
            logger.warning(f"[Ollama] Error: {e}")
            raise

    def stream(self, messages: list, system: str = "") -> Generator[str, None, None]:
        try:
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            payload = {
                "model": self.model,
                "messages": full_messages,
                "stream": True,
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
