# core/logging.py — Structured JSON & Console Logging Framework for JARVIS MK37
from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from brjarvis.core.paths import paths

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Context Var for Correlation IDs across async tasks
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="sys-init")

# Suppress only specific known-noisy third-party libraries.
# REMOVED: warnings.filterwarnings("ignore") — blanket suppression hides real bugs.
_NOISY_LOGGERS = [
    "urllib3",
    "chromadb",
    "google.auth",
    "asyncio",
    "httpx",
    "httpcore",
    "onnxruntime",
    "PIL",
    "comtypes",
]


def _suppress_noisy_loggers() -> None:
    """Silence known verbose third-party loggers at WARNING level."""
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


class JSONFormatter(logging.Formatter):
    """Machine-readable JSON log formatter with context vars."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "module": record.module,
            "line": record.lineno,
        }
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["data"] = record.extra_data
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Human-readable colorized console log formatter."""

    COLORS = {
        "DEBUG":    "\033[36m",   # Cyan
        "INFO":     "\033[32m",   # Green
        "WARNING":  "\033[33m",   # Yellow
        "ERROR":    "\033[31m",   # Red
        "CRITICAL": "\033[41m",   # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        cid = correlation_id_ctx.get()
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"{color}[{record.levelname[:1]} {timestamp}][{cid[:8]}]{self.RESET}"
        msg = f"{prefix} \033[1m{record.name}\033[0m: {record.getMessage()}"
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        return msg


def setup_logger(name: str = "JARVIS", level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """Configure and return a structured logger instance.

    Logs are written to both a colorized console handler and a JSONL file.
    The LOGS_DIR is created lazily on first file-handler setup to avoid
    creating directories at import time before the working directory is set.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    _suppress_noisy_loggers()

    # Avoid adding duplicate handlers if already configured
    if any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        return logger

    # Console Handler
    console_level = os.environ.get("JARVIS_CONSOLE_LOG_LEVEL", "WARNING").upper()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level, logging.WARNING))
    console_handler.setFormatter(ColoredConsoleFormatter())
    logger.addHandler(console_handler)

    # File Handler (JSONL) — created lazily here, not at import time
    if log_to_file:
        try:
            logs_dir = paths.LOG_ROOT
            logs_dir.mkdir(parents=True, exist_ok=True)
            file_path = logs_dir / "jarvis.jsonl"
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        except OSError as exc:
            logger.warning(f"[Logging] Could not create log file handler: {exc}")

    return logger


class LogTimer:
    """Context manager for timing operational code blocks."""

    def __init__(self, logger: logging.Logger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.debug(f"▶ Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        if exc_type:
            self.logger.error(
                f"❌ Failed: {self.operation_name} after {duration_ms:.2f}ms ({exc_val})"
            )
        else:
            self.logger.info(
                f"✓ Completed: {self.operation_name} in {duration_ms:.2f}ms"
            )


logger = setup_logger("JARVIS")
