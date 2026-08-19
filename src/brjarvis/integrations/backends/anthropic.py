# backends/anthropic.py — JARVIS MK37 Anthropic (Claude) Backend
"""
Anthropic (Claude) backend connector for BR Core.
Safe initialization, standardized error handling, and text streaming.
"""

from __future__ import annotations

import logging
import os
from typing import Generator

from .base import BaseBackend

logger = logging.getLogger("JARVIS.Claude")


class ClaudeBackend(BaseBackend):
    """Anthropic Claude backend with proper message format conversion."""

    def __init__(self, model: str = None, api_key: str = None):

        try:
            from brjarvis.config.models import get_model

            default_model = get_model("claude") or "claude-sonnet-4-20250514"
        except Exception:
            default_model = "claude-sonnet-4-20250514"

        self.model = model or default_model
        self.client = None

        _api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not _api_key:
            try:
                from brjarvis.core.config import get_config

                _api_key = (get_config().secrets.anthropic_api_key or "").strip()
            except Exception:
                pass
        if not _api_key:
            try:
                import json

                from brjarvis.core.paths import paths

                cfg_file = paths.CONFIG_ROOT / "api_keys.json"
                if cfg_file.exists():
                    data = json.loads(cfg_file.read_text(encoding="utf-8"))
                    for k, v in data.items():
                        if str(k).lower().strip() in ("anthropic_api_key", "claude_api_key") and str(v).strip():
                            _api_key = str(v).strip()
                            break
            except Exception:
                pass

        if _api_key:
            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=_api_key)
                logger.info("Using model: %s", self.model)
            except ImportError:
                logger.warning("anthropic package is not installed.")

    @property
    def name(self) -> str:
        return "Claude"

    @property
    def model_name(self) -> str:
        return self.model

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "Anthropic client is not initialized. "
                "Ensure ANTHROPIC_API_KEY is configured in your environment or .env, "
                "and the 'anthropic' pip package is installed."
            )

    def _format_messages(self, messages: list, system: str = "") -> tuple[list, str]:
        """Convert standard messages to Anthropic format (system is separate)."""
        formatted = []
        sys_prompt = system
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                if not sys_prompt:
                    sys_prompt = content
                continue
            formatted.append({"role": role, "content": content})
        return formatted, sys_prompt

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        try:
            self._ensure_client()
            formatted, sys_prompt = self._format_messages(messages, system)

            kwargs = {
                "model": self.model,
                "max_tokens": 8192,
                "messages": formatted,
            }
            if sys_prompt:
                kwargs["system"] = sys_prompt

            response = self.client.messages.create(**kwargs)
            # Handle multi-block responses: collect text from all TextBlock items
            text_parts = []
            for block in response.content:
                if hasattr(block, "text") and isinstance(block.text, str):
                    text_parts.append(block.text)
                elif hasattr(block, "type") and block.type == "tool_use":
                    # Tool-use block: serialize as JSON string for orchestrator
                    import json as _json

                    text_parts.append(
                        _json.dumps(
                            {
                                "tool_use": True,
                                "name": getattr(block, "name", ""),
                                "input": getattr(block, "input", {}),
                            }
                        )
                    )
            return "".join(text_parts)
        except Exception as e:
            logger.error("Claude Error: %s", e)
            raise

    def stream(self, messages: list, system: str = "") -> Generator[str, None, None]:
        try:
            self._ensure_client()
            formatted, sys_prompt = self._format_messages(messages, system)

            kwargs = {
                "model": self.model,
                "max_tokens": 8192,
                "messages": formatted,
            }
            if sys_prompt:
                kwargs["system"] = sys_prompt

            with self.client.messages.stream(**kwargs) as stream_res:
                for text in stream_res.text_stream:
                    yield text
        except Exception as e:
            yield f"\n[Claude Stream Error: {e}]"


# Alias for legacy compatibility
AnthropicBackend = ClaudeBackend
