# backends/gemini.py — JARVIS MK37 Primary AI Backend (Gemini)
"""
Robust Gemini backend — the ONLY required backend for JARVIS MK37.
Supports: text completion, streaming, vision, grounding (web search).
Falls back gracefully on any model error.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Generator

from backends.base import BaseBackend


def _load_api_key() -> str:
    """Load Gemini API key from env or config/api_keys.json."""
    for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(env, "").strip()
        if val:
            return val

    cfg_path = Path(__file__).parent.parent / "config" / "api_keys.json"
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            key = data.get("gemini_api_key", "").strip()
            if key:
                return key
        except Exception:
            pass

    raise ValueError(
        "No Gemini API key found.\n"
        "Set GEMINI_API_KEY env var OR add 'gemini_api_key' to config/api_keys.json"
    )


class GeminiBackend(BaseBackend):
    """
    Full-featured Gemini backend for JARVIS MK37.
    Model priority: gemini-3.5-flash → gemini-3.1-pro-preview → ...
    """

    FALLBACK_MODELS = [
        "gemini-3.5-flash-low",
        "gemini-3-flash",
        "gemini-3.6-flash-high",
        "gemini-3-flash-agent",
        "gemini-pro-agent",
        "gemini-2.0-flash",
    ]

    def __init__(self, model: str = None, api_key: str = None):
        self._use_openai_client = False
        self._client = None

        # Check if local proxy gateway should be used (default: True)
        use_proxy = os.environ.get("JARVIS_ROUTE_GEMINI_TO_GATEWAY", "true").lower() == "true"
        if use_proxy:
            try:
                from openai import OpenAI
                from config.models import get_model_config
                cfg = get_model_config()
                base_url = cfg.get("openai_base_url", "http://localhost:8045/v1")
                api_key_val = os.environ.get("OPENAI_API_KEY", "").strip() or cfg.get("openai_api_key", "").strip() or "local-proxy-key"
                self._client = OpenAI(base_url=base_url, api_key=api_key_val)
                self._use_openai_client = True
                self.model = model or self._pick_model()
                print(f"[Gemini] Routed via local proxy gateway: {base_url} (model: {self.model})")
                return
            except Exception as e:
                print(f"[Gemini] Failed to initialize local proxy client: {e}. Falling back to direct Google client.")

        # Standard direct Google fallback
        try:
            self.api_key = api_key or _load_api_key()
        except ValueError as e:
            raise e

        self.model = model or self._pick_model()
        from google import genai
        self._client = genai.Client(api_key=self.api_key)
        print(f"[Gemini] [OK] Using model: {self.model}")

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def model_name(self) -> str:
        return self.model

    def _pick_model(self) -> str:
        """Try to use the best available model."""
        try:
            from config.models import get_model
            cfg_model = get_model("gemini")
            if cfg_model:
                return cfg_model
        except Exception:
            pass
        return self.FALLBACK_MODELS[0]

    @property
    def client(self):
        return self._client

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        """Standard completion — used by the ReAct orchestrator."""
        if self._use_openai_client:
            full_messages = []
            if system and system.strip():
                full_messages.append({"role": "system", "content": system.strip()})
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content")
                if content is not None:
                    if isinstance(content, str) and content.strip():
                        full_messages.append({"role": role, "content": content.strip()})
                    elif not isinstance(content, str):
                        full_messages.append({"role": role, "content": str(content)})
            if not full_messages or not any(m.get("content") for m in full_messages if m.get("role") != "system"):
                full_messages.append({"role": "user", "content": "Hello"})

            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                print(f"[Gemini Proxy] Model {self.model} failed: {e} — trying fallbacks...")
                for fallback in self.FALLBACK_MODELS:
                    if fallback == self.model:
                        continue
                    try:
                        response = self._client.chat.completions.create(
                            model=fallback,
                            messages=full_messages,
                        )
                        return response.choices[0].message.content or ""
                    except Exception:
                        pass
                raise e

        # Direct Google client path
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content")
            if content is not None:
                content_str = str(content).strip() if isinstance(content, str) else str(content)
                if content_str:
                    contents.append({"role": role, "parts": [{"text": content_str}]})

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        config = {}
        if system and system.strip():
            config["system_instruction"] = system.strip()

        for attempt, model in enumerate(self.FALLBACK_MODELS):
            try:
                target_model = self.model if attempt == 0 else model
                response = self.client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config if config else None,
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e).lower()
                if "quota" in err_str or "rate" in err_str or "429" in err_str:
                    import random
                    backoff = min(60, (2 ** attempt) + random.uniform(0, 1))
                    print(f"[Gemini] Rate limit on {target_model}, backoff {backoff:.1f}s...")
                    time.sleep(backoff)
                if attempt == len(self.FALLBACK_MODELS) - 1:
                    raise
                print(f"[Gemini] Model {target_model} failed: {e} — trying next...")
                time.sleep(0.5)

        return ""

    def stream(self, messages: list, system: str = "") -> Generator[str, None, None]:
        """Streaming completion."""
        if self._use_openai_client:
            full_messages = []
            if system and system.strip():
                full_messages.append({"role": "system", "content": system.strip()})
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content")
                if content is not None:
                    if isinstance(content, str) and content.strip():
                        full_messages.append({"role": role, "content": content.strip()})
                    elif not isinstance(content, str):
                        full_messages.append({"role": role, "content": str(content)})
            if not full_messages or not any(m.get("content") for m in full_messages if m.get("role") != "system"):
                full_messages.append({"role": "user", "content": "Hello"})

            try:
                stream_res = self._client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                    stream=True
                )
                for chunk in stream_res:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                yield f"\n[Gemini Proxy Stream Error: {e}]"
                return

        # Direct Google client path
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content")
            if content is not None:
                content_str = str(content).strip() if isinstance(content, str) else str(content)
                if content_str:
                    contents.append({"role": role, "parts": [{"text": content_str}]})

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        config = {}
        if system and system.strip():
            config["system_instruction"] = system.strip()

        try:
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config if config else None,
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"\n[Stream error: {e}]"

    def complete_with_search(self, query: str, system: str = "") -> str:
        """Completion with Google Search grounding (real-time web data)."""
        if self._use_openai_client:
            return self.complete([{"role": "user", "content": query}], system)

        # Direct path
        try:
            config = {"tools": [{"google_search": {}}]}
            if system:
                config["system_instruction"] = system

            response = self.client.models.generate_content(
                model=self.model,
                contents=query,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            print(f"[Gemini] Search grounding failed: {e} — falling back to regular completion")
            return self.complete([{"role": "user", "content": query}], system)

    def complete_with_vision(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        """Vision completion — analyze an image."""
        if self._use_openai_client:
            import base64
            try:
                b64 = base64.b64encode(image_bytes).decode("ascii")
                data_url = f"data:{mime_type};base64,{b64}"
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ]
                    }
                ]
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                return f"Vision error: {e}"

        # Direct path
        import base64
        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            contents = [{
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                    {"text": prompt},
                ]
            }]
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
            )
            return response.text or ""
        except Exception as e:
            return f"Vision error: {e}"

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """Transcribe audio bytes using Gemini."""
        if self._use_openai_client:
            try:
                import io
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "audio.wav"
                response = self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return (response.text or "").strip()
            except Exception as e:
                print(f"[Gemini Proxy] Transcription failed: {e}")
                return ""

        # Direct path
        import base64
        try:
            b64 = base64.b64encode(audio_bytes).decode("ascii")
            contents = [{
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                    {"text": "Transcribe this audio clip exactly. If you only hear noise or silence, return an empty string. Output only the transcription, no chat, no intro, no comments."},
                ]
            }]
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"[Gemini] Transcription failed: {e}")
            return ""

    def quick(self, prompt: str) -> str:
        """Quick single-prompt completion — for planning, routing, etc."""
        return self.complete([{"role": "user", "content": prompt}])

    def ping(self, timeout: float = 10.0) -> bool:
        """Health check via completion to leverage fallback model chain."""
        try:
            start = time.monotonic()
            result = self.complete([{"role": "user", "content": "ping"}])
            elapsed = time.monotonic() - start
            is_err = "error" in result.lower() or "failed" in result.lower()
            return bool(result) and not is_err and elapsed < timeout
        except Exception:
            return False
