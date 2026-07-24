# backends/openai_compat.py — JARVIS MK37 OpenAI-Compatible Backend
"""
OpenAI (GPT) backend connector for BR Core.
Supports custom base_url for local proxies (e.g., localhost:8045).
"""
from __future__ import annotations

import os
import traceback
from typing import Generator

from backends.base import BaseBackend


class OpenAIBackend(BaseBackend):
    """OpenAI-compatible backend with base_url support for local proxies."""

    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        try:
            from config.models import get_model
            default_model = get_model("gpt") or "gpt-4o"
        except Exception:
            default_model = "gpt-4o"

        self.model = (
            model
            or os.environ.get("OPENAI_MODEL", "").strip()
            or default_model
        )
        self.client = None

        _api_key = api_key or os.environ.get("OPENAI_API_KEY", "").strip() or "local-proxy-key"
        _base_url = base_url or os.environ.get("OPENAI_BASE_URL", "").strip() or "http://localhost:8045/v1"

        if _api_key:
            try:
                from openai import OpenAI
                client_kwargs = {"api_key": _api_key}
                if _base_url:
                    client_kwargs["base_url"] = _base_url
                self.client = OpenAI(**client_kwargs)
                suffix = f" via {_base_url}" if _base_url else ""
                print(f"[OpenAI] [OK] Using model: {self.model}{suffix}")
            except ImportError:
                print("[OpenAI] Warning: openai package is not installed.")
        else:
            print("[OpenAI] No API key configured — backend disabled.")

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model_name(self) -> str:
        return self.model

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "OpenAI client is not initialized. "
                "Ensure OPENAI_API_KEY is configured in your environment or .env, "
                "and the 'openai' pip package is installed."
            )

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        try:
            self._ensure_client()

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
            return response.choices[0].message.content
        except Exception as e:
            print(f"[OpenAI] Error: {e}")
            raise

    def stream(self, messages: list, system: str = "") -> Generator[str, None, None]:
        try:
            self._ensure_client()

            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            stream_res = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                stream=True
            )
            for chunk in stream_res:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[OpenAI Stream Error: {e}]"

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcribe audio bytes using OpenAI Whisper API."""
        try:
            self._ensure_client()
            import io
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename
            
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"[OpenAI] Transcription failed: {e}")
            return ""

    def ping(self, timeout: float = 3.0) -> bool:
        """Quick health check — try a minimal completion."""
        try:
            self._ensure_client()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                timeout=timeout,
            )
            return bool(response.choices)
        except Exception:
            return False
