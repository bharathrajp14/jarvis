# core/timeouts.py — Parameterized Timeout Config for BR JARVIS
from __future__ import annotations

from pydantic import BaseModel, Field


class TimeoutConfig(BaseModel):
    """Timeout configuration settings for various subsystems and tools in BR JARVIS."""
    
    ocr_timeout: float = Field(default=10.0, description="Timeout in seconds for OCR operations")
    tool_exec_timeout: float = Field(default=30.0, description="Default timeout in seconds for executing tool commands")
    voice_stt_timeout: float = Field(default=5.0, description="Speech-To-Text phrase listening timeout limit")
    voice_tts_timeout: float = Field(default=10.0, description="Neural Text-To-Speech conversion timeout")
    api_request_timeout: float = Field(default=15.0, description="Timeout for external API backend HTTP calls")
    desktop_action_delay: float = Field(default=0.1, description="Standard pause delay after pyautogui operations")


_default_timeout_config = TimeoutConfig()


def get_timeout_config() -> TimeoutConfig:
    """Retrieve global timeout settings model."""
    global _default_timeout_config
    return _default_timeout_config
