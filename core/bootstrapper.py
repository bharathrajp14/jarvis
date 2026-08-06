# core/bootstrapper.py — Unified System Bootstrapper
"""
Unified System Bootstrapper for BR JARVIS.
Standardizes environment initialization, encoding setup, API key validation,
and runtime singleton construction across all entry points.
"""
from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    load_dotenv()
except ImportError:
    pass

from core.bootstrap import AssistantRuntime, build_assistant_runtime


class CoreBootstrapper:
    """Unified System Bootstrapper Singleton for BR JARVIS."""

    _initialized: bool = False
    _base_dir: Path = Path(__file__).resolve().parent.parent

    @classmethod
    def setup_environment(cls) -> Dict[str, Any]:
        """Configure platform encoding, environment variables, and return status."""
        if cls._initialized:
            return cls.get_status()

        # Fix Windows terminal UTF-8 encoding
        if sys.platform == "win32":
            os.environ["PYTHONIOENCODING"] = "utf-8"
            try:
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                if hasattr(sys.stderr, "reconfigure"):
                    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.exception('Boot critical exception encountered in core/bootstrapper.py')
                else:
                    import logging
                    logging.getLogger(__name__).exception('Boot critical exception')
                raise e
        env_file = cls._base_dir / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv  # type: ignore[import-not-found]
                load_dotenv(env_file)
            except ImportError:
                pass

        cls._initialized = True
        return cls.get_status()

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get diagnostic status of system environment and keys."""
        config_path = cls._base_dir / "config" / "api_keys.json"
        api_keys = {
            "Gemini": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
            "Claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "GPT": bool(os.environ.get("OPENAI_API_KEY")),
            "Mistral": bool(os.environ.get("MISTRAL_API_KEY")),
            "NVIDIA": bool(os.environ.get("NVIDIA_API_KEY")),
        }

        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                if cfg.get("gemini_api_key"):
                    api_keys["Gemini"] = True
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.exception('Boot critical exception encountered in core/bootstrapper.py')
                else:
                    import logging
                    logging.getLogger(__name__).exception('Boot critical exception')
                raise e
        return {
            "initialized": cls._initialized,
            "platform": platform.system(),
            "python_version": sys.version.split()[0],
            "base_dir": str(cls._base_dir),
            "api_keys": api_keys,
        }

    @classmethod
    def initialize_runtime(cls, *, use_vector_memory: bool = True) -> AssistantRuntime:
        """Setup environment and build the AssistantRuntime singleton."""
        cls.setup_environment()
        return build_assistant_runtime(use_vector_memory=use_vector_memory)
