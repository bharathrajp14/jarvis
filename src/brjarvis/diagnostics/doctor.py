# src/brjarvis/diagnostics/doctor.py — Canonical Diagnostic & Self-Healing Engine for BR JARVIS MK40.2+
from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.Doctor")

PYTHON = sys.executable


def _credential_status(
    reference: str, env_names: tuple[str, ...], config_value: Any = None
) -> tuple[bool, Optional[str]]:
    """Return presence and a non-secret source label for one provider credential."""
    for env_name in env_names:
        if os.environ.get(env_name, "").strip():
            return True, f"environment:{env_name}"
    if config_value:
        return True, "configuration"
    try:
        from brjarvis.security.credentials import get_credential_vault

        if get_credential_vault().get_credential(reference):
            return True, "os-keyring"
    except Exception as exc:
        logger.debug("Credential vault unavailable while checking %s: %s", reference, exc)
    return False, None


def check_module(name: str) -> tuple[bool, str]:
    """Check if a python module is available and return status/version."""
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", None)
        if not ver:
            try:
                ver = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                ver = "OK"
        return True, str(ver)
    except Exception as e:
        if "DisplayConnectionError" in type(e).__name__ or "display" in str(e).lower():
            return True, f"Installed ({type(e).__name__})"
        return False, str(e)


def auto_install_package(pkg: str, import_name: str) -> bool:
    """Multi-method robust installer for missing Python packages."""
    methods = [
        ("Standard pip", [PYTHON, "-m", "pip", "install", pkg, "--quiet"]),
        ("Upgraded pip", [PYTHON, "-m", "pip", "install", "--upgrade", pkg, "--quiet"]),
        ("Break-system-packages pip", [PYTHON, "-m", "pip", "install", pkg, "--break-system-packages", "--quiet"]),
        ("User scope pip", [PYTHON, "-m", "pip", "install", "--user", pkg, "--quiet"]),
        ("No-deps pip", [PYTHON, "-m", "pip", "install", pkg, "--no-deps", "--quiet"]),
    ]

    for _, cmd in methods:
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=90)
            ok, _ = check_module(import_name)
            if ok or res.returncode == 0:
                return True
        except Exception:
            pass

    req_files = [paths.PROJECT_ROOT / "requirements.txt", paths.PROJECT_ROOT / "requirements-dev.txt"]
    for req in req_files:
        if req.exists():
            try:
                subprocess.run(
                    [PYTHON, "-m", "pip", "install", "-r", str(req), "--quiet"], capture_output=True, timeout=120
                )
                ok, _ = check_module(import_name)
                if ok:
                    return True
            except Exception:
                pass

    return check_module(import_name)[0]


class DoctorReport(TypedDict):
    python_packages: Dict[str, Tuple[bool, str]]
    system_tools: Dict[str, Optional[str]]
    api_keys: Dict[str, bool]
    api_key_sources: Dict[str, Optional[str]]
    paths_status: Dict[str, bool]
    subsystems_status: Dict[str, str]
    dependency_summary: Dict[str, int]
    python_runtime: Dict[str, str]
    repair_actions: List[Dict[str, str]]
    overall_health: str


def run_diagnostics_audit(auto_repair: bool = False) -> DoctorReport:
    """Run full diagnostic audit across all subsystems and return structured report."""
    python_deps = {
        "PySide6": "PySide6",
        "google-genai": "google.genai",
        "openai": "openai",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "rich": "rich",
        "psutil": "psutil",
        "sounddevice": "sounddevice",
        "SpeechRecognition": "speech_recognition",
        "pyperclip": "pyperclip",
        "pyautogui": "pyautogui",
        "pyyaml": "yaml",
        "Pillow": "PIL",
        "mss": "mss",
        "edge-tts": "edge_tts",
        "numpy": "numpy",
        "opencv-python": "cv2",
        "requests": "requests",
        "httpx": "httpx",
        "ddgs": "ddgs",
        "beautifulsoup4": "bs4",
        "playwright": "playwright",
        "youtube-transcript-api": "youtube_transcript_api",
        "anthropic": "anthropic",
        "python-multipart": "multipart",
        "python-docx": "docx",
        "pypdf": "pypdf",
        "fpdf2": "fpdf",
        "openpyxl": "openpyxl",
        "pydantic": "pydantic",
        "keyring": "keyring",
        "cryptography": "cryptography",
    }

    core_package_names = {
        "google-genai",
        "fastapi",
        "uvicorn",
        "python-multipart",
        "rich",
        "psutil",
        "pyyaml",
        "requests",
        "httpx",
        "pydantic",
        "keyring",
        "cryptography",
    }
    pkg_results: Dict[str, Tuple[bool, str]] = {}
    repair_actions: List[Dict[str, str]] = []
    for pkg_name, imp_name in python_deps.items():
        ok, ver = check_module(imp_name)
        if not ok and auto_repair:
            repaired = auto_install_package(pkg_name, imp_name)
            repair_actions.append(
                {
                    "package": pkg_name,
                    "import": imp_name,
                    "status": "repaired" if repaired else "failed",
                }
            )
            ok = repaired and check_module(imp_name)[0]
            ver = "Repaired" if ok else "Failed Repair"
        pkg_results[pkg_name] = (ok, ver)

    # Capability checks distinguish executables from importable Python modules.
    if sys.platform == "win32":
        binary_tools = {
            "C Compiler": ["gcc", "clang", "cl"],
            "FFmpeg Engine": ["ffmpeg"],
        }
        fallback_tools = {
            "GUI Automation": ["pyautogui"],
            "Screenshot Utilities": ["mss", "Pillow"],
            "Audio Engines": ["sounddevice", "edge-tts"],
        }
    else:
        binary_tools = {
            "C Compiler": ["gcc", "clang"],
            "FFmpeg Engine": ["ffmpeg"],
        }
        fallback_tools = {
            "GUI Automation": ["xdotool", "pyautogui"],
            "Screenshot Utilities": ["scrot", "import", "mss"],
            "Audio Engines": ["espeak-ng", "pw-play", "aplay", "sounddevice"],
        }

    sys_results: Dict[str, Optional[str]] = {}
    for group, candidates in binary_tools.items():
        sys_results[group] = next((candidate for candidate in candidates if shutil.which(candidate)), None)
    for group, candidates in fallback_tools.items():
        found = next((candidate for candidate in candidates if shutil.which(candidate)), None)
        if found is None:
            for candidate in candidates:
                module_name = {"Pillow": "PIL", "edge-tts": "edge_tts"}.get(candidate, candidate)
                if check_module(module_name)[0]:
                    found = f"{candidate} (Python module)"
                    break
        sys_results[group] = found

    # Credential status is deliberately boolean plus a non-secret source label.
    cfg_secrets = None
    try:
        from brjarvis.core.config import get_config

        cfg_secrets = get_config().secrets
    except Exception as exc:
        logger.debug("Configuration secrets unavailable to doctor: %s", exc)

    provider_specs = {
        "Gemini": ("gemini-api-key", ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "gemini_api_key"),
        "Claude": ("anthropic-api-key", ("ANTHROPIC_API_KEY",), "anthropic_api_key"),
        "GPT": ("openai-api-key", ("OPENAI_API_KEY",), "openai_api_key"),
        "DeepSeek": ("deepseek-api-key", ("DEEPSEEK_API_KEY", "OPENROUTER_API_KEY"), "deepseek_api_key"),
        "Mistral": ("mistral-api-key", ("MISTRAL_API_KEY",), "mistral_api_key"),
        "NVIDIA": ("nvidia-api-key", ("NVIDIA_API_KEY",), "nvidia_api_key"),
    }
    key_map: Dict[str, bool] = {}
    key_sources: Dict[str, Optional[str]] = {}
    for provider, (reference, env_names, config_attr) in provider_specs.items():
        present, source = _credential_status(
            reference,
            env_names,
            getattr(cfg_secrets, config_attr, None) if cfg_secrets else None,
        )
        key_map[provider] = present
        key_sources[provider] = source
    has_any_backend = (
        any(key_map.values())
        or bool(os.environ.get("OPENAI_BASE_URL"))
        or bool(os.environ.get("OLLAMA_HOST"))
        or bool(os.environ.get("BRJARVIS_PROXY_BASE_URL"))
    )

    # Paths
    path_map = {
        "PROJECT_ROOT": paths.PROJECT_ROOT,
        "SOURCE_ROOT": paths.SOURCE_ROOT,
        "RUNTIME_ROOT": paths.RUNTIME_ROOT,
        "LOG_ROOT": paths.LOG_ROOT,
        "STATE_ROOT": paths.STATE_ROOT,
        "ARTIFACT_ROOT": paths.ARTIFACT_ROOT,
        "WORKSPACE_ROOT": paths.WORKSPACE_ROOT,
    }
    paths_status = {name: path.is_dir() for name, path in path_map.items()}

    # Subsystems
    subsystems_status: Dict[str, str] = {}
    career_ok = False
    try:
        from brjarvis.career.crm.database import get_career_crm_db

        db = get_career_crm_db()
        cnt = db.get_stats().get("applications_count", 0)
        subsystems_status["Career OS"] = f"OK ({cnt} applications)"
        career_ok = True
    except Exception as e:
        subsystems_status["Career OS"] = f"Degraded ({e})"

    tools_ok = False
    try:
        from brjarvis.tools.registry import get_registry_status

        t_stat = get_registry_status()
        reg_count = t_stat["registered"]
        fail_count = len(t_stat["failed"])
        if fail_count > 0:
            subsystems_status["Tool Registry"] = f"Degraded ({reg_count} registered, {fail_count} failed)"
        else:
            subsystems_status["Tool Registry"] = f"OK ({reg_count} tools active)"
        tools_ok = reg_count >= 10
    except Exception as e:
        subsystems_status["Tool Registry"] = f"Degraded ({e})"

    skills_ok = False
    try:
        from brjarvis.skills import load_skills

        skills = load_skills()
        subsystems_status["Skills Subsystem"] = f"OK ({len(skills)} skills loaded)"
        skills_ok = True
    except Exception as e:
        subsystems_status["Skills Subsystem"] = f"Degraded ({e})"

    available_count = sum(1 for ok, _ in pkg_results.values() if ok)
    missing_core = sum(1 for name in core_package_names if not pkg_results.get(name, (False, ""))[0])
    missing_optional = len(pkg_results) - available_count - missing_core
    dependency_summary = {
        "total": len(pkg_results),
        "available": available_count,
        "missing_core": missing_core,
        "missing_optional": max(0, missing_optional),
    }
    all_core_pkg_ok = missing_core == 0
    all_paths_ok = all(paths_status.values())
    python_runtime = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": str(Path(PYTHON).resolve()),
        "virtualenv": "true" if os.environ.get("VIRTUAL_ENV") or hasattr(sys, "real_prefix") else "false",
    }

    # Truthful derived overall health calculation
    if not all_paths_ok:
        overall = "FAILED (Missing core paths)"
    elif not all_core_pkg_ok:
        overall = "DEGRADED (Missing core Python dependencies)"
    elif not has_any_backend:
        overall = "NOT_READY (AI backends unconfigured)"
    elif not tools_ok or not career_ok or not skills_ok:
        overall = "DEGRADED (Subsystem issues detected)"
    else:
        overall = "HEALTHY"

    return {
        "python_packages": pkg_results,
        "system_tools": sys_results,
        "api_keys": key_map,
        "api_key_sources": key_sources,
        "paths_status": paths_status,
        "subsystems_status": subsystems_status,
        "dependency_summary": dependency_summary,
        "python_runtime": python_runtime,
        "repair_actions": repair_actions,
        "overall_health": overall,
    }
