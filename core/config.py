# core/config.py — Structured Pydantic v2 Configuration Engine for JARVIS MK37
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
MODELS_JSON = CONFIG_DIR / "models.json"


class AssistantConfig(BaseModel):
    name: str = Field(default="BR", description="Name of the assistant")
    wake_word: str = Field(default="jarvis", description="Wake word for voice listening")
    offline_stt: bool = Field(default=False, description="Use offline Whisper model")
    whisper_model: str = Field(default="base", description="Whisper model tier")
    voice_language: str = Field(default="en", description="Primary language code")
    voice_name: str = Field(default="Charon", description="TTS voice name")


class ModelConfig(BaseModel):
    default_backend: str = Field(default="gemini", description="Default primary LLM backend")
    gemini: str = Field(default="gemini-3.6-flash-high", description="Gemini model ID")
    gemini_code: str = Field(default="gemini-3.1-pro-high", description="Gemini Code model ID")
    gemini_reasoning: str = Field(default="gemini-3.1-pro-high", description="Gemini Reasoning model ID")
    claude: str = Field(default="claude-sonnet-4-6", description="Claude model ID")
    gpt: str = Field(default="gemini-3.6-flash-high", description="GPT model ID")
    ollama: str = Field(default="llama3.3", description="Ollama local model ID")
    nvidia: str = Field(default="meta/llama-3.1-70b-instruct", description="NVIDIA NIM model ID")
    mistral: str = Field(default="mistral-large-latest", description="Mistral model ID")
    planner_model: str = Field(default="gemini-3.6-flash-high", description="Planning model ID")
    fast_model: str = Field(default="gemini-3-flash", description="Fast inference model ID")
    voice_live: str = Field(default="models/gemini-3.1-flash-live-preview", description="Voice Live model ID")


class SystemConfig(BaseModel):
    environment: str = Field(default="development", description="Execution environment")
    debug: bool = Field(default=False, description="Debug mode flag")
    log_level: str = Field(default="INFO", description="Logging verbosity (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field(default="json", description="Log output format (console, json)")
    workspace_dir: str = Field(default=str(BASE_DIR / "workspace"), description="Workspace root path")
    max_workers: int = Field(default=3, description="Maximum parallel task workers")


class HardwareConfig(BaseModel):
    max_cpu_percent: float = Field(default=90.0, description="CPU alert threshold")
    max_memory_percent: float = Field(default=85.0, description="RAM alert threshold")
    enable_native_bridge: bool = Field(default=True, description="Enable C native acceleration bridge")


class JarvisConfig(BaseModel):
    assistant: AssistantConfig = Field(default_factory=AssistantConfig)
    models: ModelConfig = Field(default_factory=ModelConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)

    @classmethod
    def load(cls) -> JarvisConfig:
        """Load configuration merging defaults, models.json, and environment variables."""
        cfg = cls()

        # 1. Load models.json if available
        if MODELS_JSON.exists():
            try:
                data = json.loads(MODELS_JSON.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if not k.startswith("_") and hasattr(cfg.models, k) and isinstance(v, str) and v.strip():
                        setattr(cfg.models, k, v.strip())
            except Exception:
                pass

        # 2. Load Environment Variable Overrides
        env = os.environ
        if env.get("JARVIS_ASSISTANT_NAME"):
            cfg.assistant.name = env["JARVIS_ASSISTANT_NAME"]
        if env.get("JARVIS_WAKE_WORD"):
            cfg.assistant.wake_word = env["JARVIS_WAKE_WORD"]
        if env.get("JARVIS_OFFLINE_STT"):
            cfg.assistant.offline_stt = env["JARVIS_OFFLINE_STT"].lower() in ("true", "1", "yes")
        if env.get("JARVIS_WHISPER_MODEL"):
            cfg.assistant.whisper_model = env["JARVIS_WHISPER_MODEL"]
        if env.get("JARVIS_DEFAULT_BACKEND"):
            cfg.models.default_backend = env["JARVIS_DEFAULT_BACKEND"]
        if env.get("JARVIS_LOG_LEVEL"):
            cfg.system.log_level = env["JARVIS_LOG_LEVEL"].upper()

        return cfg


_global_config: Optional[JarvisConfig] = None


def get_config(force_reload: bool = False) -> JarvisConfig:
    global _global_config
    if _global_config is None or force_reload:
        _global_config = JarvisConfig.load()
    return _global_config
