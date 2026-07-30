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
        "gemini-3.6-flash-high",
        "gemini-3-flash",
        "gemini-3.6-flash-medium",
        "gemini-3.1-pro-high",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
    ]

    def __init__(self, model: str = None, api_key: str = None):
        self._use_openai_client = False
        self._client = None
        self._explicit_model = model

        # Check if local proxy gateway should be used (default: True)
        use_proxy = os.environ.get("JARVIS_ROUTE_GEMINI_TO_GATEWAY", "true").lower() == "true"
        if use_proxy:
            try:
                from openai import OpenAI  # type: ignore
                from config.models import get_model_config
                cfg = get_model_config()
                base_url = cfg.get("openai_base_url", "http://localhost:8045/v1")
                api_key_val = os.environ.get("OPENAI_API_KEY", "").strip() or cfg.get("openai_api_key", "").strip() or "none"
                self._client = OpenAI(base_url=base_url, api_key=api_key_val)
                self._use_openai_client = True
                self.model = model or self._pick_model()
                print(f"[Gemini] Routed via local proxy gateway: {base_url} (auto-model routing enabled)")
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

    @property
    def available(self) -> bool:
        return self._client is not None or getattr(self, "_genai_client", None) is not None

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

    def _get_target_model(self, messages: list, system: str = "") -> str:
        if self._explicit_model:
            return self._explicit_model
        try:
            from config.complexity_router import select_model_for_prompt
            return select_model_for_prompt(messages=messages, system=system)
        except Exception:
            return self.model

    @property
    def client(self):
        return self._client

    def complete(self, messages: list, system: str = "", tools: list = None, max_tokens: int = None) -> str:
        """Standard completion — used by the ReAct orchestrator with flexible token budget."""
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

        target_model = self._get_target_model(messages, system)

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
                    model=target_model,
                    messages=full_messages,
                    max_tokens=max_output_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                print(f"[Gemini Proxy] Model {target_model} failed: {e} — trying fallbacks...")
                for fallback in self.FALLBACK_MODELS:
                    if fallback == target_model:
                        continue
                    try:
                        response = self._client.chat.completions.create(
                            model=fallback,
                            messages=full_messages,
                            max_tokens=max_output_tokens,
                        )
                        return response.choices[0].message.content or ""
                    except Exception:
                        pass
                print(f"[Gemini Proxy] All proxy models exhausted/failed. Falling back to direct Google client...")
                try:
                    direct_key = _load_api_key()
                    from google import genai
                    direct_client = genai.Client(api_key=direct_key)
                    contents = []
                    for msg in messages:
                        role = "user" if msg.get("role") == "user" else "model"
                        c = msg.get("content")
                        if c: contents.append({"role": role, "parts": [{"text": str(c)}]})
                    if not contents: contents = [{"role": "user", "parts": [{"text": "Hello"}]}]
                    resp = direct_client.models.generate_content(model="gemini-2.5-flash", contents=contents)
                    return resp.text or ""
                except Exception as ex_direct:
                    print(f"[Gemini Direct Fallback Error]: {ex_direct}")
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
        target_model = self._get_target_model(messages, system)
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
                    model=target_model,
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
                model=target_model,
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
        """Transcribe audio bytes using Gemini (Proxy or Direct API)."""
        import base64
        import io

        if self._use_openai_client and self._client:
            try:
                # 1. Try standard OpenAI whisper endpoint
                file_payload = ("audio.wav", audio_bytes, mime_type)
                try:
                    response = self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=file_payload,
                    )
                    return (response.text or "").strip()
                except Exception as ex_stt:
                    # 2. Multimodal Chat Fallback for proxy gateways returning HTTP 415
                    b64 = base64.b64encode(audio_bytes).decode("ascii")
                    try:
                        resp = self._client.chat.completions.create(
                            model=self.model or "gpt-4o",
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Transcribe this audio clip exactly. Return only the transcription, no intro, no comments."},
                                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}}
                                ]
                            }]
                        )
                        return (resp.choices[0].message.content or "").strip()
                    except Exception:
                        pass
            except Exception as e:
                print(f"[Gemini Proxy] Transcription note: {e}")

        # Direct Google Gemini API path
        try:
            if hasattr(self, "client") and self.client and hasattr(self.client, "models"):
                b64 = base64.b64encode(audio_bytes).decode("ascii")
                contents = [{
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": b64}},
                        {"text": "Transcribe this audio clip exactly. Output only the transcription, no intro, no comments."},
                    ]
                }]
                response = self.client.models.generate_content(
                    model=self.model or "gemini-2.5-flash",
                    contents=contents,
                )
                return (response.text or "").strip()
        except Exception as e:
            print(f"[Gemini Direct] Transcription failed: {e}")

        return ""

    def quick(self, prompt: str) -> str:
        """Quick single-prompt completion — for planning, routing, etc."""
        return self.complete([{"role": "user", "content": prompt}])

    def ping(self, timeout: float = 30.0) -> bool:
        """Health check via completion to leverage fallback model chain."""
        try:
            start = time.monotonic()
            result = self.complete([{"role": "user", "content": "ping"}])
            elapsed = time.monotonic() - start
            is_err = "error" in result.lower() or "failed" in result.lower()
            return bool(result) and not is_err and elapsed < timeout
        except Exception:
            return False
