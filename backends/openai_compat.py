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
        self._explicit_model = model or os.environ.get("OPENAI_MODEL", "").strip() or None
        try:
            from config.models import get_model
            default_model = get_model("gpt") or "gemini-3.6-flash-high"
        except Exception:
            default_model = "gemini-3.6-flash-high"

        self.model = self._explicit_model or default_model
        self.client = None

        _api_key = api_key or os.environ.get("OPENAI_API_KEY", "").strip() or "local-proxy-key"
        _base_url = base_url or os.environ.get("OPENAI_BASE_URL", "").strip() or "http://localhost:8045/v1"

        if _api_key:
            try:
                from openai import OpenAI  # type: ignore
                client_kwargs = {"api_key": _api_key}
                if _base_url:
                    client_kwargs["base_url"] = _base_url
                self.client = OpenAI(**client_kwargs)
                suffix = f" via {_base_url}" if _base_url else ""
                print(f"[OpenAI] [OK] Auto model routing active (default: {self.model}){suffix}")
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

    def _get_target_model(self, messages: list, system: str = "") -> str:
        if self._explicit_model:
            return self._explicit_model
        try:
            from config.complexity_router import select_model_for_prompt
            return select_model_for_prompt(messages=messages, system=system)
        except Exception:
            return self.model

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "OpenAI client is not initialized. "
                "Ensure OPENAI_API_KEY is configured in your environment or .env, "
                "and the 'openai' pip package is installed."
            )

    def complete(self, messages: list, system: str = "", tools: list = None, max_tokens: int = None) -> str:
        try:
            self._ensure_client()

            try:
                from config.complexity_router import (
                    analyze_complexity,
                    get_recommended_token_limit,
                    prune_messages_to_fit_budget,
                )
                complexity = analyze_complexity(messages=messages, system=system)
                max_output_tokens = get_recommended_token_limit(complexity, user_max_tokens=max_tokens)
                messages = prune_messages_to_fit_budget(messages, system=system)
            except Exception:
                max_output_tokens = max_tokens or 2048

            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            target_model = self._get_target_model(messages, system)

            kwargs = {
                "model": target_model,
                "messages": full_messages,
                "max_tokens": max_output_tokens,
            }
            if tools:
                kwargs["tools"] = tools

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"[OpenAI] Primary request failed ({e}) — attempting Gemini fallback...")
            try:
                from backends.gemini import GeminiBackend
                fallback_backend = GeminiBackend()
                return fallback_backend.complete(messages=messages, system=system, tools=tools)
            except Exception as ex_fb:
                print(f"[OpenAI Fallback Error]: {ex_fb}")
                raise e

    def stream(self, messages: list, system: str = "") -> Generator[str, None, None]:
        try:
            self._ensure_client()

            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            target_model = self._get_target_model(messages, system)

            stream_res = self.client.chat.completions.create(
                model=target_model,
                messages=full_messages,
                stream=True
            )
            for chunk in stream_res:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[OpenAI Stream Error: {e}]"

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcribe audio bytes using 100% Offline Local Whisper, falling back to API if offline unavailable."""
        import base64
        import io

        # 0. Prioritize 100% Offline Local Whisper (sub-30ms, no network 503 errors)
        try:
            from voice.whisper_local import transcribe as whisper_transcribe, is_available
            if is_available():
                text = whisper_transcribe(audio_bytes)
                if text and text.strip():
                    return text.strip()
        except Exception:
            pass

        try:
            self._ensure_client()
            file_payload = (filename, audio_bytes, "audio/wav")
            try:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=file_payload,
                )
                return (response.text or "").strip()
            except Exception as ex_stt:
                # Fall back to base64 inline audio chat completion for proxies returning HTTP 415/503
                try:
                    b64 = base64.b64encode(audio_bytes).decode("ascii")
                    resp = self.client.chat.completions.create(
                        model=self.model or "gemini-2.5-flash",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Transcribe this audio clip exactly. Return only the transcription, no intro, no comments."},
                                {"type": "image_url", "image_url": {"url": f"data:audio/wav;base64,{b64}"}}
                            ]
                        }]
                    )
                    return (resp.choices[0].message.content or "").strip()
                except Exception:
                    return ""
        except Exception as e:
            print(f"[OpenAIBackend] Transcription error: {e}")
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
