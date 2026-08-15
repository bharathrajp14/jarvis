# core/config.py — Strongly Typed Canonical Configuration Engine for BR JARVIS
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
MODELS_JSON = CONFIG_DIR / "models.json"
API_KEYS_JSON = CONFIG_DIR / "api_keys.json"

_logger = logging.getLogger("JARVIS.Config")

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_ENVIRONMENTS = {"development", "production", "testing", "staging"}


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class AssistantConfig(BaseModel):
    name: str = Field(default="BR", description="Name of the assistant")
    wake_word: str = Field(default="jarvis", description="Wake word for voice listening")
    offline_stt: bool = Field(default=False, description="Use offline Whisper model")
    whisper_model: str = Field(default="base", description="Whisper model tier")
    voice_language: str = Field(default="en", description="Primary language code")
    voice_name: str = Field(default="Charon", description="TTS voice name")


class ModelConfig(BaseModel):
    default_backend: str = Field(default="gemini", description="Default primary LLM backend")
    gemini: str = Field(default="gemini-2.5-flash", description="Gemini model ID")
    gemini_code: str = Field(default="gemini-2.5-pro", description="Gemini Code model ID")
    gemini_reasoning: str = Field(default="gemini-2.5-pro", description="Gemini Reasoning model ID")
    claude: str = Field(default="claude-sonnet-4-6", description="Claude model ID")
    gpt: str = Field(default="gpt-4o-mini", description="GPT model ID")
    ollama: str = Field(default="llama3.3", description="Ollama local model ID")
    nvidia: str = Field(default="meta/llama-3.1-70b-instruct", description="NVIDIA NIM model ID")
    mistral: str = Field(default="mistral-large-latest", description="Mistral model ID")
    planner_model: str = Field(default="gemini-2.5-flash", description="Planning model ID")
    fast_model: str = Field(default="gemini-2.0-flash", description="Fast inference model ID")
    voice_live: str = Field(default="models/gemini-2.0-flash-live-001", description="Voice Live model ID")


class SecurityConfig(BaseModel):
    server_api_key: Optional[str] = Field(default=None, description="Server authorization API key")
    permission_mode: str = Field(default="confirm_destructive", description="Policy permission mode")
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins"
    )
    session_ttl_seconds: float = Field(default=86400.0, description="Web session time-to-live")
    ws_ticket_ttl_seconds: float = Field(default=60.0, description="WebSocket one-time ticket TTL")
    require_https: bool = Field(default=False, description="Enforce HTTPS/WSS in production")


class WebConfig(BaseModel):
    host: str = Field(default="127.0.0.1", description="HTTP and WebSocket bind address")
    port: int = Field(default=8000, description="HTTP and WebSocket port")
    open_browser: bool = Field(default=True, description="Open browser interface on launch")


class SecretsConfig(BaseModel):
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    deepseek_api_key: Optional[str] = Field(default=None, description="DeepSeek API key")
    mistral_api_key: Optional[str] = Field(default=None, description="Mistral API key")
    nvidia_api_key: Optional[str] = Field(default=None, description="NVIDIA API key")
    github_api_key: Optional[str] = Field(default=None, description="GitHub token")


class SystemConfig(BaseModel):
    environment: str = Field(default="development", description="Execution environment (development, production, testing)")
    debug: bool = Field(default=False, description="Debug mode flag")
    log_level: str = Field(default="INFO", description="Logging verbosity")
    log_format: str = Field(default="json", description="Log output format (console, json)")
    workspace_dir: str = Field(default=str(BASE_DIR / "workspace"), description="Workspace root path")
    max_workers: int = Field(default=4, description="Maximum parallel task workers")

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        normalized = str(v).upper().strip()
        if normalized not in _LOG_LEVELS:
            _logger.warning("Invalid log_level '%s'. Defaulting to INFO.", v)
            return "INFO"
        return normalized

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: Any) -> str:
        normalized = str(v).lower().strip()
        if normalized not in _ENVIRONMENTS:
            _logger.warning("Invalid environment '%s'. Defaulting to development.", v)
            return "development"
        return normalized


class HardwareConfig(BaseModel):
    max_cpu_percent: float = Field(default=90.0, description="CPU alert threshold")
    max_memory_percent: float = Field(default=85.0, description="RAM alert threshold")
    enable_native_bridge: bool = Field(default=True, description="Enable C native acceleration bridge")


class JarvisConfig(BaseModel):
    assistant: AssistantConfig = Field(default_factory=AssistantConfig)
    models: ModelConfig = Field(default_factory=ModelConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)

    def validate_production(self) -> None:
        """Validate configuration for production deployments."""
        if self.system.environment == "production":
            has_llm_key = any([
                self.secrets.gemini_api_key,
                self.secrets.openai_api_key,
                self.secrets.anthropic_api_key,
                self.secrets.deepseek_api_key,
                self.secrets.mistral_api_key,
                self.secrets.nvidia_api_key,
            ])
            if not has_llm_key and not os.environ.get("OPENAI_BASE_URL"):
                raise ConfigurationError("Production startup failed: No valid LLM backend credentials or proxy gateway configured.")
            if not self.security.server_api_key:
                _logger.warning("[Production Config Alert] SERVER_API_KEY is not set. API endpoints are running in open mode.")

    @classmethod
    def load(cls, overrides: Optional[Dict[str, Any]] = None) -> "JarvisConfig":
        """Load configuration adhering to strict precedence:
        1. Defaults
        2. Config files (config/models.json, config/api_keys.json)
        3. .env file
        4. Environment variables (os.environ)
        5. Explicit runtime overrides
        """
        # Ensure .env is loaded
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                pass

        cfg = cls()

        # 2. Config files
        if MODELS_JSON.exists():
            try:
                data = json.loads(MODELS_JSON.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if not k.startswith("_") and hasattr(cfg.models, k) and isinstance(v, str) and v.strip():
                        setattr(cfg.models, k, v.strip())
            except Exception as exc:
                _logger.debug("Failed to read models.json: %s", exc)

        if API_KEYS_JSON.exists():
            try:
                data = json.loads(API_KEYS_JSON.read_text(encoding="utf-8"))
                if data.get("server_api_key"):
                    cfg.security.server_api_key = str(data["server_api_key"]).strip()
                if data.get("gemini_api_key"):
                    cfg.secrets.gemini_api_key = str(data["gemini_api_key"]).strip()
                if data.get("github developer_api_key"):
                    cfg.secrets.github_api_key = str(data["github developer_api_key"]).strip()
            except Exception as exc:
                _logger.debug("Failed to read api_keys.json: %s", exc)

        # 3 & 4. Environment Variables
        env = os.environ
        if env.get("JARVIS_ASSISTANT_NAME"):
            cfg.assistant.name = env["JARVIS_ASSISTANT_NAME"].strip()
        if env.get("JARVIS_WAKE_WORD"):
            cfg.assistant.wake_word = env["JARVIS_WAKE_WORD"].strip()
        if env.get("JARVIS_OFFLINE_STT"):
            cfg.assistant.offline_stt = env["JARVIS_OFFLINE_STT"].lower() in ("true", "1", "yes")
        if env.get("JARVIS_WHISPER_MODEL"):
            cfg.assistant.whisper_model = env["JARVIS_WHISPER_MODEL"].strip()
        if env.get("JARVIS_DEFAULT_BACKEND"):
            cfg.models.default_backend = env["JARVIS_DEFAULT_BACKEND"].strip()
        if env.get("JARVIS_LOG_LEVEL"):
            cfg.system.log_level = env["JARVIS_LOG_LEVEL"].upper().strip()
        if env.get("JARVIS_DEBUG"):
            cfg.system.debug = env["JARVIS_DEBUG"].lower() in ("true", "1", "yes")
        if env.get("JARVIS_ENVIRONMENT"):
            cfg.system.environment = env["JARVIS_ENVIRONMENT"].lower().strip()
        if env.get("BR_SERVER_HOST") or env.get("HOST"):
            cfg.web.host = (env.get("BR_SERVER_HOST") or env.get("HOST", "127.0.0.1")).strip()
        if env.get("BR_SERVER_PORT") or env.get("PORT"):
            port_val = env.get("BR_SERVER_PORT") or env.get("PORT", "8000")
            if str(port_val).isdigit():
                cfg.web.port = int(port_val)
        if env.get("JARVIS_SERVER_API_KEY"):
            cfg.security.server_api_key = env["JARVIS_SERVER_API_KEY"].strip()
        if env.get("JARVIS_PERMISSION_MODE"):
            cfg.security.permission_mode = env["JARVIS_PERMISSION_MODE"].strip()
        if env.get("JARVIS_CORS_ORIGINS"):
            origins = [o.strip() for o in env["JARVIS_CORS_ORIGINS"].split(",") if o.strip()]
            if origins:
                cfg.security.cors_origins = origins

        # LLM Keys
        if env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY"):
            cfg.secrets.gemini_api_key = (env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY", "")).strip()
        if env.get("OPENAI_API_KEY"):
            cfg.secrets.openai_api_key = env["OPENAI_API_KEY"].strip()
        if env.get("ANTHROPIC_API_KEY"):
            cfg.secrets.anthropic_api_key = env["ANTHROPIC_API_KEY"].strip()
        if env.get("DEEPSEEK_API_KEY"):
            cfg.secrets.deepseek_api_key = env["DEEPSEEK_API_KEY"].strip()
        if env.get("MISTRAL_API_KEY"):
            cfg.secrets.mistral_api_key = env["MISTRAL_API_KEY"].strip()
        if env.get("NVIDIA_API_KEY"):
            cfg.secrets.nvidia_api_key = env["NVIDIA_API_KEY"].strip()

        # 5. Overrides
        if overrides:
            for section, values in overrides.items():
                if hasattr(cfg, section) and isinstance(values, dict):
                    target_sec = getattr(cfg, section)
                    for k, v in values.items():
                        if hasattr(target_sec, k):
                            setattr(target_sec, k, v)

        return cfg


_global_config: Optional[JarvisConfig] = None
_config_lock = threading.Lock()


def get_config(force_reload: bool = False) -> JarvisConfig:
    """Return the global singleton JarvisConfig (thread-safe)."""
    global _global_config
    if _global_config is not None and not force_reload:
        return _global_config

    with _config_lock:
        if _global_config is None or force_reload:
            _global_config = JarvisConfig.load()
    return _global_config
