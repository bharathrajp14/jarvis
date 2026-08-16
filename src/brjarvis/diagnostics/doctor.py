# src/brjarvis/diagnostics/doctor.py — Canonical Diagnostic & Self-Healing Engine for BR JARVIS MK40.2+
from __future__ import annotations

import importlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict, cast

from brjarvis.core.paths import paths
from brjarvis.core.version import VERSION, BUILD, CODENAME

logger = logging.getLogger("JARVIS.Doctor")

PYTHON = sys.executable


def check_module(name: str) -> tuple[bool, str]:
    """Check if a python module is available and return status/version."""
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "OK")
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
                subprocess.run([PYTHON, "-m", "pip", "install", "-r", str(req), "--quiet"], capture_output=True, timeout=120)
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
    paths_status: Dict[str, bool]
    subsystems_status: Dict[str, str]
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
        "duckduckgo-search": "duckduckgo_search",
        "beautifulsoup4": "bs4",
        "playwright": "playwright",
        "youtube-transcript-api": "youtube_transcript_api",
        "anthropic": "anthropic",
        "python-docx": "docx",
        "pypdf": "pypdf",
        "fpdf2": "fpdf",
        "openpyxl": "openpyxl",
        "pydantic": "pydantic",
    }

    pkg_results: Dict[str, Tuple[bool, str]] = {}
    for pkg_name, imp_name in python_deps.items():
        ok, ver = check_module(imp_name)
        if not ok and auto_repair:
            ok = auto_install_package(pkg_name, imp_name)
            ver = "Repaired" if ok else "Failed Repair"
        pkg_results[pkg_name] = (ok, ver)

    # CLI tools
    if sys.platform == "win32":
        cli_tools = {
            "C Compiler": ["gcc", "clang", "cl"],
            "GUI Automation": ["pyautogui"],
            "Screenshot Utilities": ["mss", "Pillow"],
            "Audio Engines": ["sounddevice", "edge-tts"],
            "FFmpeg Engine": ["ffmpeg"],
        }
    else:
        cli_tools = {
            "C Compiler": ["gcc", "clang"],
            "GUI Automation": ["xdotool"],
            "Screenshot Utilities": ["scrot", "import"],
            "Audio Engines": ["espeak-ng", "pw-play", "aplay"],
            "FFmpeg Engine": ["ffmpeg"],
        }

    sys_results: Dict[str, Optional[str]] = {}
    for group, bins in cli_tools.items():
        found = None
        for b in bins:
            if shutil.which(b):
                found = b
                break
        sys_results[group] = found

    # Keys & Backends
    key_map = {
        "Gemini": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        "Claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "GPT": bool(os.environ.get("OPENAI_API_KEY")),
        "Mistral": bool(os.environ.get("MISTRAL_API_KEY")),
        "NVIDIA": bool(os.environ.get("NVIDIA_API_KEY")),
    }
    has_any_backend = any(key_map.values()) or bool(os.environ.get("OPENAI_BASE_URL")) or bool(os.environ.get("OLLAMA_HOST"))

    # Paths
    paths_status = {
        "PROJECT_ROOT": paths.PROJECT_ROOT.exists(),
        "SOURCE_ROOT": paths.SOURCE_ROOT.exists(),
        "RUNTIME_ROOT": paths.RUNTIME_ROOT.exists(),
        "LOG_ROOT": paths.LOG_ROOT.exists(),
        "STATE_ROOT": paths.STATE_ROOT.exists(),
        "ARTIFACT_ROOT": paths.ARTIFACT_ROOT.exists(),
        "WORKSPACE_ROOT": paths.WORKSPACE_ROOT.exists(),
    }

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

    all_pkg_ok = all(r[0] for r in pkg_results.values())
    all_paths_ok = all(paths_status.values())

    # Truthful derived overall health calculation
    if not all_paths_ok:
        overall = "FAILED (Missing core paths)"
    elif not all_pkg_ok:
        overall = "DEGRADED (Missing Python dependencies)"
    elif not has_any_backend:
        overall = "NOT_READY (AI backends unconfigured)"
    elif not tools_ok or not career_ok:
        overall = "DEGRADED (Subsystem issues detected)"
    else:
        overall = "HEALTHY"

    return {
        "python_packages": pkg_results,
        "system_tools": sys_results,
        "api_keys": key_map,
        "paths_status": paths_status,
        "subsystems_status": subsystems_status,
        "overall_health": overall,
    }
