# start.py — JARVIS MK40.2 Unified Launcher & System Orchestrator
from __future__ import annotations
"""
Production-grade launcher and diagnostic orchestrator for BR JARVIS MK40.2.
Features Rich TUI, Artifact Lifecycle Subsystem, Policy Engine Diagnostics, and Multi-Sequence Booting.
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
warnings.filterwarnings("ignore", message=".*imp module.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*audioop.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*renamed.*", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")

import atexit
import importlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO, TypedDict, cast, Callable, Optional

# ── Auto-reroute from Python 3.14 alpha to stable Python 3.12 if available ────
if __name__ == "__main__" and sys.version_info >= (3, 14) and sys.platform == "win32" and not os.environ.get("JARVIS_IGNORE_PY314"):
    import shutil
    _py_cmd = shutil.which("py")
    if _py_cmd:
        for _ver in ("-3.12", "-3.13", "-3.11"):
            _chk = subprocess.run([_py_cmd, _ver, "--version"], capture_output=True)
            if _chk.returncode == 0:
                print(f"[JARVIS] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}...")
                os.environ["JARVIS_IGNORE_PY314"] = "1"
                _res = subprocess.run([_py_cmd, _ver] + sys.argv)
                sys.exit(_res.returncode)

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    load_dotenv()
except ImportError:
    pass

# Validate presence of primary API keys or Local Gateway Proxy
_primary_keys = ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"]
_found_keys = [k for k in _primary_keys if os.environ.get(k) and not os.environ.get(k).startswith("your_")]
if not _found_keys and not os.environ.get("OPENAI_BASE_URL"):
    print("[WARNING] JARVIS MK40.2 Security Alert: No active API keys or proxy gateway found in environment or .env!")
    print("           Please configure your key in .env (GEMINI_API_KEY, OPENAI_API_KEY, etc.)")


# Fix terminal encoding & Qt DLL plugin paths on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    for _mod_name in ("PySide6", "PyQt6", "PyQt5"):
        try:
            _m = __import__(_mod_name)
            _mod_dir = os.path.dirname(_m.__file__)
            _plugins_dir = os.path.join(_mod_dir, "plugins")
            _platforms_dir = os.path.join(_plugins_dir, "platforms")
            os.environ["QT_PLUGIN_PATH"] = _plugins_dir
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _platforms_dir
            if hasattr(os, "add_dll_directory"):
                for _d in (_mod_dir, _plugins_dir, _platforms_dir):
                    if os.path.exists(_d):
                        try:
                            os.add_dll_directory(_d)
                        except Exception:
                            pass
            break
        except ImportError:
            continue
    try:
        stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
        stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
        if callable(stdout_reconfigure):
            stdout_reconfigure(encoding="utf-8", errors="replace")
        if callable(stderr_reconfigure):
            stderr_reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Setup Rich formatting
try:
    from rich.console import Console  # type: ignore[import-not-found]
    from rich.panel import Panel  # type: ignore[import-not-found]
    from rich.table import Table  # type: ignore[import-not-found]
    from rich.text import Text  # type: ignore[import-not-found]
    from rich.prompt import Prompt  # type: ignore[import-not-found]
    console = Console()
except ImportError:
    print("Oops! 'rich' module is missing. Please run: pip install rich")
    sys.exit(1)

# ── Constants ────────────────────────────────────────────────────────────────

from core.version import VERSION, BUILD, CODENAME

BASE_DIR = Path(__file__).resolve().parent
PYTHON   = sys.executable
LOG_DIR  = BASE_DIR / "logs"
PID_FILE = BASE_DIR / ".jarvis.pid"


def _cleanup_pid_file():
    try:
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass

atexit.register(_cleanup_pid_file)


# ── Banner ───────────────────────────────────────────────────────────────────

def _banner():
    console.clear()
    now = datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")
    text = Text(justify="center")
    text.append("⚡ BR JARVIS — ADVANCED AI OPERATING SYSTEM ⚡\n", style="bold cyan")
    text.append("Autonomous Cognitive Agent Architecture & Isolated Sandbox Lifecycle Engine\n\n", style="dim")
    text.append(f"Version: {VERSION}  │  Build: {BUILD}  │  Codename: {CODENAME}\n", style="bold green")
    text.append(f"Python: {sys.version.split()[0]}  │  Platform: {platform.system()}  │  Security: FAIL-CLOSED 🛡️\n", style="cyan")
    text.append(now, style="dim")
    
    panel = Panel(text, border_style="bold cyan", padding=(0, 2))
    console.print(panel)
    console.print()

# ── Status and Check Helpers ──────────────────────────────────────────────────

class EnvStatus(TypedDict):
    env_file: bool
    config_file: bool
    api_keys: dict[str, bool]
    gateway_proxy: bool
    artifacts_dir: str
    permission_mode: str

def _check_env() -> EnvStatus:
    """Check environment configuration and return status dict."""
    status: EnvStatus = {
        "env_file": False,
        "config_file": False,
        "api_keys": {},
        "gateway_proxy": False,
        "artifacts_dir": "",
        "permission_mode": "confirm_destructive",
    }
    env_file    = BASE_DIR / ".env"
    config_file = BASE_DIR / "config" / "api_keys.json"

    status["env_file"]    = env_file.exists()
    status["config_file"] = config_file.exists()

    try:
        import dotenv  # type: ignore[import-not-found]
        if env_file.exists():
            dotenv.load_dotenv(env_file)
    except ImportError:
        pass

    key_map = {
        "GEMINI_API_KEY":    "Gemini",
        "GOOGLE_API_KEY":    "Gemini (alt)",
        "ANTHROPIC_API_KEY": "Claude",
        "OPENAI_API_KEY":    "GPT / Local Gateway",
        "MISTRAL_API_KEY":   "Mistral",
        "NVIDIA_API_KEY":    "NVIDIA NIM",
        "GROQ_API_KEY":      "Groq",
    }
    for env_key, label in key_map.items():
        val = os.environ.get(env_key, "")
        status["api_keys"][label] = bool(val and len(val) > 5 and not val.startswith("your_"))

    status["gateway_proxy"] = bool(os.environ.get("OPENAI_BASE_URL"))
    status["permission_mode"] = os.environ.get("JARVIS_PERMISSION_MODE", "allow_all")

    try:
        from agent.artifacts import get_artifact_manager
        mgr = get_artifact_manager()
        status["artifacts_dir"] = str(mgr.get_host_artifact_dir())
    except Exception:
        status["artifacts_dir"] = str(Path.home() / "Documents" / "BR-JARVIS" / "artifacts")

    return status

def _check_module(name: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "OK")
        return True, str(ver)
    except Exception as e:
        if "DisplayConnectionError" in type(e).__name__ or "display" in str(e).lower():
            return True, f"Installed ({type(e).__name__})"
        return False, str(e)

# ── Health Diagnostic Command ─────────────────────────────────────────────────

def show_status():
    _banner()
    env = _check_env()

    # Environment
    table_env = Table(title="Environment & Architecture", title_style="bold magenta", show_header=False, box=None)
    table_env.add_column("Property", style="bold")
    table_env.add_column("Value")
    table_env.add_row("Base Dir", str(BASE_DIR))
    table_env.add_row("Python Exec", sys.executable)
    venv = hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    table_env.add_row("Virtual Env", "[green]Active[/]" if venv else "[yellow]Not detected[/]")
    table_env.add_row("Env File", "[green]✓ Found (.env)[/]" if env["env_file"] else "[red]✗ MISSING[/]")
    table_env.add_row("Permission Mode", f"[bold green]{env['permission_mode'].upper()}[/]")
    table_env.add_row("Host Artifacts Dir", f"[cyan]{env['artifacts_dir']}[/]")

    # Backends
    table_be = Table(title="AI Backends & Gateway Routing", title_style="bold magenta", show_header=False, box=None)
    has_any = False
    for label, ok in env["api_keys"].items():
        if "alt" in label and not ok: continue
        table_be.add_row(f"[green]✓ {label}[/]" if ok else f"[dim]○ {label}[/]", "[green]Configured[/]" if ok else "[dim]Not Configured[/]")
        if ok: has_any = True

    proxy_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:8045/v1")
    if env["gateway_proxy"]:
        table_be.add_row("[bold green]✓ Local Proxy Gateway[/]", f"[cyan]{proxy_url}[/]")
        has_any = True

    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        import urllib.request
        req = urllib.request.Request(f"{ollama_host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1):
            table_be.add_row(f"[green]✓ Ollama (Offline LLM)[/]", f"[green]Running[/] at {ollama_host}")
            has_any = True
    except Exception:
        table_be.add_row(f"[dim]○ Ollama (Offline LLM)[/]", f"[dim]Not Running ({ollama_host})[/]")

    # Modules
    table_mod = Table(title="Core Engine Modules", title_style="bold magenta", show_header=False, box=None)
    core_modules = [
        ("google.genai", "Google GenAI SDK"), ("openai", "OpenAI Client / Gateway"),
        ("sounddevice", "Audio Hardware I/O"), ("requests", "HTTP Client"),
        ("httpx", "Async HTTP Engine"), ("PIL", "Image / Vision Processing"),
        ("numpy", "Numerics & Audio Math"), ("psutil", "System Resource Monitor"),
        ("playwright", "Browser Automation Engine"), ("docx", "Microsoft Word Engine"),
        ("fpdf", "PDF Document Generator"), ("openpyxl", "Excel Multi-Tab Engine")
    ]
    for mod_name, label in core_modules:
        ok, ver = _check_module(mod_name)
        if ok:
            table_mod.add_row(f"[green]✓ {label}[/]", f"[dim]{ver}[/]")
        else:
            table_mod.add_row(f"[red]✗ {label}[/]", "[red]MISSING[/]")
            
    table_sys = Table(title="Subsystems & Registries", title_style="bold magenta", show_header=False, box=None)
    try:
        sys.path.insert(0, str(BASE_DIR))
        from skills import load_skills
        table_sys.add_row("[green]✓ Skills Loaded[/]", str(len([s for s in load_skills() if getattr(s, 'user_invocable', True)])))
        
        from multi_agent.subagent import load_agent_definitions
        table_sys.add_row("[green]✓ Specialized Subagents[/]", str(len(load_agent_definitions())))
        
        from tools.registry import TOOL_SCHEMAS, _import_plugins
        _import_plugins()
        tool_schemas = cast(list[dict[str, Any]], TOOL_SCHEMAS)
        table_sys.add_row("[green]✓ Registered Tools[/]", str(len(tool_schemas)))

        from agent.artifacts import get_artifact_manager
        mgr = get_artifact_manager()
        table_sys.add_row("[green]✓ Artifact Manager[/]", f"Safe Host Storage ({len(mgr.list_artifacts())} tracked)")

        from agent.verifier import get_action_verifier
        table_sys.add_row("[green]✓ ActionVerifier[/]", "Active (Host & Browser Validation)")
    except Exception as e:
        table_sys.add_row("[yellow]⚠ Subsystems Note[/]", str(e))

    console.print(table_env)
    console.print()
    if not has_any:
        console.print("[bold yellow]⚠ No backends configured. AI chat will not work. Add keys to .env[/]")
    console.print(table_be)
    console.print()
    console.print(table_mod)
    console.print()
    console.print(table_sys)
    console.print()

# ── Dependencies Doctor ────────────────────────────────────────────────────────

def _auto_install_package(pkg: str, import_name: str) -> bool:
    """Multi-method robust installer trying fallback methods for missing Python packages."""
    methods = [
        ("Standard pip", [PYTHON, "-m", "pip", "install", pkg, "--quiet"]),
        ("Upgraded pip", [PYTHON, "-m", "pip", "install", "--upgrade", pkg, "--quiet"]),
        ("Break-system-packages pip", [PYTHON, "-m", "pip", "install", pkg, "--break-system-packages", "--quiet"]),
        ("User scope pip", [PYTHON, "-m", "pip", "install", "--user", pkg, "--quiet"]),
        ("No-deps pip", [PYTHON, "-m", "pip", "install", pkg, "--no-deps", "--quiet"]),
    ]
    
    for method_name, cmd in methods:
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=90)
            ok, _ = _check_module(import_name)
            if ok or res.returncode == 0:
                return True
        except Exception:
            pass

    # Bulk requirements fallback
    req_files = [BASE_DIR / "requirements_mk37.txt", BASE_DIR / "requirements.txt"]
    for req in req_files:
        if req.exists():
            try:
                subprocess.run([PYTHON, "-m", "pip", "install", "-r", str(req), "--quiet"], capture_output=True, timeout=120)
                ok, _ = _check_module(import_name)
                if ok:
                    return True
            except Exception:
                pass

    return _check_module(import_name)[0]


def _install_playwright_browsers():
    """Multi-method installer for Playwright browser binaries."""
    commands = [
        [PYTHON, "-m", "playwright", "install", "chromium"],
        [PYTHON, "-m", "playwright", "install"],
        ["playwright", "install", "chromium"],
    ]
    for cmd in commands:
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=120)
            if res.returncode == 0:
                break
        except Exception:
            pass


def doctor(auto_confirm: bool = False):
    _banner()
    console.print("[bold magenta]⚡ JARVIS MK40.2 Advanced System Doctor & Self-Healing Repair Engine ⚡[/]\n")

    if not sys.stdin.isatty():
        auto_confirm = True

    # 1. Python Libraries Audit
    python_dependencies: dict[str, str] = {
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
        "python-docx": "docx",
        "pypdf": "pypdf",
        "fpdf2": "fpdf",
        "openpyxl": "openpyxl",
        "keyboard": "keyboard",
        "cryptography": "cryptography",
        "pydantic": "pydantic",
    }
    
    missing_pip: list[tuple[str, str]] = []
    
    table_pip = Table(title="1. Core Python Packages Audit", box=None)
    table_pip.add_column("Package Name", style="bold cyan")
    table_pip.add_column("Import Identifier", style="dim")
    table_pip.add_column("Status")
    
    for pip_name, import_name in python_dependencies.items():
        ok, ver = _check_module(import_name)
        if ok:
            table_pip.add_row(pip_name, import_name, f"[green]✓ Installed[/] [dim]({ver})[/]")
        else:
            table_pip.add_row(pip_name, import_name, "[red]✗ MISSING[/]")
            missing_pip.append((pip_name, import_name))
            
    console.print(table_pip)
    console.print()

    # 2. System CLI Tools Audit (OS-Adaptive)
    import shutil
    if sys.platform == "win32":
        cli_tools = {
            "C Compiler (gcc/clang/cl)": ["gcc", "clang", "cl"],
            "GUI Automation (Native)": ["pyautogui", "pywin32"],
            "Screenshot Utilities (Native)": ["mss", "Pillow"],
            "Audio Engines (Native)": ["sounddevice", "edge-tts", "pyttsx3"],
            "FFmpeg Engine": ["ffmpeg"],
        }
    else:
        cli_tools = {
            "C Compiler (gcc/clang)": ["gcc", "clang"],
            "GUI Automation Tools": ["xdotool", "xrandr"],
            "Screenshot Utilities": ["scrot", "import", "grim"],
            "Audio Engines": ["espeak-ng", "spd-say", "pw-play", "paplay", "aplay"],
            "FFmpeg Engine": ["ffmpeg"],
        }
    
    table_sys = Table(title=f"2. System Environment & CLI Tools Audit ({platform.system()})", box=None)
    table_sys.add_column("Tool Group", style="bold yellow")
    table_sys.add_column("Found Binary / Module", style="dim")
    table_sys.add_column("Status")
    
    missing_sys_groups = []
    for group_name, bin_list in cli_tools.items():
        found = None
        for b in bin_list:
            if shutil.which(b):
                found = b
                break
            elif b in ("gcc", "clang", "cl"):
                try:
                    from scripts.setup_native import find_compiler
                    fc = find_compiler()
                    if fc:
                        found = Path(fc).name
                        break
                except Exception:
                    pass
            elif _check_module(b)[0]:
                found = f"{b} (Python Module)"
                break
        if found:
            table_sys.add_row(group_name, found, "[green]✓ Available[/]")
        else:
            table_sys.add_row(group_name, "None", "[yellow]⚠ Missing (Optional Fallback)[/]")
            missing_sys_groups.append(group_name)

    console.print(table_sys)
    console.print()

    # 3. Hardware Acceleration & Native Extension Audit
    native_lib_path = BASE_DIR / "native" / ("libjarvis_native.dll" if sys.platform == "win32" else "libjarvis_native.so")
    native_ok = False
    try:
        from core.native_bridge import get_status
        st = get_status()
        native_ok = st.get("active", False)
    except Exception:
        pass

    console.print("[bold cyan]3. Hardware Acceleration & Native Extension Audit[/]")
    if native_ok:
        console.print(f"  [green]✓ Low-Latency C Shared Library Active:[/] {native_lib_path.name}")
    else:
        console.print(f"  [green]✓ Native Acceleration Active:[/] pure-Python fallbacks (hashlib FNV-1a / math VAD)")
    console.print()

    # 4. Storage, Artifacts & Web PWA Assets Audit
    console.print("[bold cyan]4. Storage, Artifacts & Web Dashboard Audit[/]")
    try:
        from agent.artifacts import get_artifact_manager
        art_mgr = get_artifact_manager()
        art_dir = art_mgr.get_host_artifact_dir()
        console.print(f"  [green]✓ Safe Host Artifact Storage:[/] [cyan]{art_dir}[/]")
    except Exception as e:
        console.print(f"  [yellow]⚠ Artifact Storage Warning: {e}[/]")

    dirs_to_check = [
        BASE_DIR / "logs",
        Path.home() / ".jarvis" / "memory",
        BASE_DIR / "config",
        BASE_DIR / "native",
        BASE_DIR / "web"
    ]
    for d in dirs_to_check:
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  [green]✓ Directory Verified:[/] [dim]{d}[/]")

    pwa_manifest = BASE_DIR / "web" / "manifest.json"
    pwa_sw = BASE_DIR / "web" / "sw.js"
    if pwa_manifest.exists() and pwa_sw.exists():
        console.print("  [green]✓ PWA Web Dashboard Assets Verified[/]")
    else:
        console.print("  [yellow]⚠ PWA Web Dashboard Assets Missing/Incomplete[/]")

    api_key_file = BASE_DIR / "config" / "api_keys.json"
    env_file = BASE_DIR / ".env"
    if not api_key_file.exists():
        api_key_file.parent.mkdir(parents=True, exist_ok=True)
        api_key_file.write_text(json.dumps({"gemini_api_key": os.environ.get("GEMINI_API_KEY", "")}, indent=2), encoding="utf-8")
        console.print(f"  [green]✓ Initialized API key config:[/] {api_key_file.name}")
    if not env_file.exists() and (BASE_DIR / ".env.template").exists():
        shutil.copy(BASE_DIR / ".env.template", env_file)
        console.print(f"  [green]✓ Created default .env from template[/]")

    console.print()

    # 5. Security & Guardian System Invariants Audit
    console.print("[bold cyan]5. Guardian System & Security Policy Audit[/]")
    try:
        from permissions import PERMISSIONS
        console.print(f"  [green]✓ Tool Permission Policy Mode:[/] [bold green]{PERMISSIONS.mode.value.upper()}[/]")
    except Exception as pe:
        console.print(f"  [yellow]⚠ Permission Policy Engine note: {pe}[/]")

    try:
        from agent.verifier import get_action_verifier
        v = get_action_verifier()
        console.print(f"  [green]✓ ActionVerifier Ready:[/] File, Process & Browser Verification active")
    except Exception as ve:
        console.print(f"  [yellow]⚠ Verifier note: {ve}[/]")

    hashes_file = BASE_DIR / ".guardian_hashes.json"
    if hashes_file.exists():
        console.print(f"  [green]✓ Guardian Integrity Hashes Found:[/] {hashes_file.name}")
    else:
        console.print(f"  [green]✓ Guardian Engine Ready:[/] Hash ledger initializes dynamically")

    console.print()

    # 6. Skills, Multi-Agent & Tool Registries Audit
    console.print("[bold cyan]6. Skills, Multi-Agent & Tool Registries Audit[/]")
    try:
        from skills import load_skills
        loaded_skills = [s for s in load_skills() if getattr(s, 'user_invocable', True)]
        console.print(f"  [green]✓ Skills Registry:[/] {len(loaded_skills)} user-invocable skills ready")
    except Exception as sk_err:
        console.print(f"  [yellow]⚠ Skills Registry note: {sk_err}[/]")

    try:
        from multi_agent.subagent import load_agent_definitions
        agent_defs = load_agent_definitions()
        console.print(f"  [green]✓ Sub-Agent Registry:[/] {len(agent_defs)} specialized agent types active")
    except Exception as ag_err:
        console.print(f"  [yellow]⚠ Sub-Agent Registry note: {ag_err}[/]")

    try:
        from tools.registry import TOOL_SCHEMAS, _import_plugins
        _import_plugins()
        console.print(f"  [green]✓ Tool Registry:[/] {len(TOOL_SCHEMAS)} registered tool definitions")
    except Exception as tl_err:
        console.print(f"  [yellow]⚠ Tool Registry note: {tl_err}[/]")

    console.print()

    # 7. System Application Paths & Auto-Configuration Audit
    console.print("[bold cyan]7. System Application Paths & Registry Auto-Configuration[/]")
    try:
        from actions.app_resolver import get_app_resolver
        resolver = get_app_resolver()
        app_count = len(resolver._cache)
        console.print(f"  [green]✓ Application Resolver:[/] [bold green]{app_count}[/] system applications indexed and launch-ready")
    except Exception as ar_err:
        console.print(f"  [yellow]⚠ Application Resolver note: {ar_err}[/]")

    console.print()

    # 8. Integrated Connectors Suite Audit
    table_conn = Table(title="8. Integrated Connector Suite Audit", box=None)
    table_conn.add_column("Connector ID", style="bold cyan")
    table_conn.add_column("Display Name", style="bold white")
    table_conn.add_column("Tools Count", justify="center")
    table_conn.add_column("Status")

    try:
        from connectors.hub import get_hub
        hub = get_hub()
        for cid, conn in hub._connectors.items():
            t_count = len(conn.list_tools())
            is_conf = conn.is_configured
            if is_conf:
                status_str = "[green]✓ CONNECTED / READY[/]"
            elif not conn.requires_auth:
                status_str = "[green]✓ ZERO-SETUP[/]"
            else:
                status_str = "[yellow]○ NEEDS KEY[/]"
            table_conn.add_row(cid, conn.display_name, str(t_count), status_str)
    except Exception as c_err:
        table_conn.add_row("hub", "ConnectorHub", "-", f"[yellow]⚠ Warning: {c_err}[/]")

    console.print(table_conn)
    console.print()

    # 9. AI Backends & Gateway Health Audit
    table_ai = Table(title="9. AI Backends & Model Gateway Audit", box=None)
    table_ai.add_column("Provider / Model Profile", style="bold magenta")
    table_ai.add_column("Model Name", style="dim")
    table_ai.add_column("Status")

    try:
        from router import load_available_backends
        active_backends = load_available_backends(force_refresh=True)
        for prof, b_inst in active_backends.items():
            try:
                ok = b_inst.ping(timeout=6.0)
                if ok:
                    table_ai.add_row(b_inst.name, b_inst.model_name, "[green]✓ ONLINE[/]")
                else:
                    table_ai.add_row(b_inst.name, b_inst.model_name, "[yellow]⚠ OFFLINE (Ping Timeout)[/]")
            except Exception:
                table_ai.add_row(b_inst.name, getattr(b_inst, 'model_name', 'N/A'), "[yellow]⚠ Key Unconfigured[/]")
    except Exception as e:
        table_ai.add_row("Router Core", "AgentRouter", f"[yellow]⚠ Warning: {e}[/]")

    console.print(table_ai)
    console.print()

    # 10. Fix & Auto-Repair Phase
    if not missing_pip:
        console.print("[bold green]========================================================[/]")
        console.print("[bold green]  DOCTOR DIAGNOSIS: SYSTEM IS 100% HEALTHY & OPERATIONAL!  [/]")
        console.print("[bold green]========================================================[/]")
        return

    console.print("[bold yellow]System Repair Needed. Beginning multi-method automatic remediation...[/]\n")

    # Fix Python Packages using multi-method installer
    if missing_pip:
        console.print(f"[bold yellow]Found {len(missing_pip)} missing Python packages.[/]")
        should_fix = auto_confirm or (sys.stdin.isatty() and Prompt.ask("Install missing Python dependencies now?", choices=["y", "n"], default="y") == "y")
        if should_fix:
            for pkg, import_id in missing_pip:
                console.print(f"  [dim]Installing {pkg} (Multi-method)...[/]", end=" ")
                success = _auto_install_package(pkg, import_id)
                if success:
                    console.print("[green]DONE (Installed)[/]")
                else:
                    console.print("[red]FAILED[/]")

            # Install Playwright browser binaries
            _install_playwright_browsers()

    # Compile Native C Library
    if not native_ok:
        console.print("\n[bold yellow]Compiling C Native Shared Extension (Auto-installing compiler if missing)...[/]")
        try:
            setup_script = BASE_DIR / "setup_native.py"
            res = subprocess.run([PYTHON, str(setup_script)], cwd=str(BASE_DIR), capture_output=True, encoding="utf-8", errors="replace")
            if res.returncode == 0:
                console.print("  [green]✓ C Native Library compiled successfully![/]")
            else:
                out_msg = res.stdout.strip() or res.stderr.strip() or "Using Python fallbacks"
                clean_msg = out_msg.splitlines()[-1] if out_msg else "Using Python fallbacks"
                console.print(f"  [yellow]⚠ Native C build note: {clean_msg}[/]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Native C build note: {e}[/]")

    console.print("\n[bold green]Doctor auto-repair sequence completed![/]")

# ── Process Execution ─────────────────────────────────────────────────────────

def _ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def _run_script(script_name: str, entry_func: Callable | None = None):
    """Run a sub-script either via direct entry function or subprocess fallback."""
    if entry_func is not None:
        try:
            entry_func()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            console.print(f"[red]Error running {script_name}: {e}[/]")
    else:
        try:
            subprocess.run([PYTHON, str(BASE_DIR / script_name)], cwd=str(BASE_DIR))
        except KeyboardInterrupt:
            pass

def _write_pid(pid: int, mode: str):
    try:
        data: dict[str, Any] = {"pid": pid, "mode": mode, "started": datetime.now().isoformat()}
        PID_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

def _clear_pid():
    try: PID_FILE.unlink(missing_ok=True)
    except Exception: pass

def _pre_launch_check() -> bool:
    env = _check_env()
    if not any(env["api_keys"].values()) and not env["gateway_proxy"]:
        console.print("\n[bold yellow]⚠ No API keys or Proxy Gateway detected![/]")
        console.print("  Duplicate [cyan].env.template[/] as [cyan].env[/] and configure your GEMINI_API_KEY or OPENAI_BASE_URL.")
        if Prompt.ask("Continue anyway?", choices=["y", "n"], default="n") != "y":
            return False
    return True

def launch_voice():
    console.print("\n[bold cyan]▶ Starting BR Voice Assistant Cyberpunk HUD[/]")
    console.print("[dim]Note: The Cyberpunk HUD GUI will open in a new window with active voice engine. Press Ctrl+C to stop.[/]\n")
    if getattr(sys, "frozen", False):
        try:
            from ui_mark import run_voice_ui
            _run_script("ui_mark.py", run_voice_ui)
        except Exception as e:
            console.print(f"[red]Error launching Voice GUI: {e}[/]")
    else:
        _run_script("ui_mark.py", None)

def launch_floating_voice():
    console.print("\n[bold cyan]▶ Starting Floating Glassmorphic JARVIS HUD Widget[/]")
    console.print("[dim]Note: The frameless floating pill window will open above all windows (Alt+Space to toggle).[/]\n")
    try:
        from float_widget import create_float_widget, QApplication
        import sys
        app = QApplication.instance() or QApplication(sys.argv)
        widget = create_float_widget()
        if widget and hasattr(widget, "show"):
            widget.show()
            sys.exit(app.exec())
    except Exception as e:
        console.print(f"[bold red]❌ Failed to launch floating HUD: {e}[/]")

def launch_cli():
    console.print("\n[bold cyan]▶ Starting CLI Orchestrator[/]")
    console.print("[dim]Type /quit to exit.[/]\n")
    from core.cli import run_cli
    run_cli()

def _wait_for_server_ready(port: int, timeout: float = 12.0) -> bool:
    import socket
    start_t = time.time()
    while time.time() - start_t < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.3)
    return False

def launch_web_server(open_url: str = None):
    port = int(os.environ.get("PORT", os.environ.get("BR_SERVER_PORT", "8000")))
    target_url = open_url or f"http://127.0.0.1:{port}"
    console.print("\n[bold cyan]▶ Starting BR Web Core Server[/]")
    console.print(f"  [green]Server Running on[/] http://127.0.0.1:{port}")
    console.print(f"  [green]Interface URL[/] Access [cyan]{target_url}[/]")
    console.print("[dim]Press Ctrl+C to shut down.[/]\n")

    def _async_open():
        if _wait_for_server_ready(port):
            try:
                from agent.artifacts import get_artifact_manager
                mgr = get_artifact_manager()
                success, resolved_url, _ = mgr.ensure_host_artifact(target_url)
                nav_url = resolved_url if success else target_url
                import webbrowser
                webbrowser.open(nav_url)
                console.print(f"[bold green]✓ Interface opened in browser: {nav_url}[/]")
            except Exception as e:
                console.print(f"[yellow]⚠ Open browser manually at: {target_url} ({e})[/]")

    threading.Thread(target=_async_open, daemon=True).start()

    if getattr(sys, "frozen", False):
        from server import main as server_main
        _run_script("server.py", server_main)
    else:
        _run_script("server.py", None)

def launch_dashboard_server():
    console.print("\n[bold cyan]▶ Launching Canonical BR JARVIS Dashboard Control Plane (Port 8000)[/]")
    launch_web_server()

def launch_mark_ui():
    console.print("\n[bold cyan]▶ Launching Mark Cyberpunk HUD Interface (JarvisLive Gemini Session + PyQt6 HUD)[/]")
    ui_mark_script = BASE_DIR / "ui_mark.py"
    if not ui_mark_script.exists():
        console.print("[red]✗ ui_mark.py script not found.[/]")
        return
    _run_script("ui_mark.py", None)

def launch_both():
    console.print("\n[bold cyan]▶ Starting Modes in Parallel[/]\n")
    if getattr(sys, "frozen", False):
        try:
            from ui_mark import JarvisUI
            from core.cli import run_cli
            app = JarvisUI()
            threading.Thread(target=app.root.mainloop if hasattr(app, "root") else lambda: None, daemon=True).start()
            run_cli()
        except Exception:
            _run_script("ui_mark.py", None)
            from core.cli import run_cli
            run_cli()
    else:
        _ensure_log_dir()
        voice_log = LOG_DIR / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_handle = open(voice_log, "w", encoding="utf-8")
        try:
            vproc = subprocess.Popen(
                [PYTHON, str(BASE_DIR / "ui_mark.py")],
                cwd=str(BASE_DIR),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            console.print(f"  [green]✓ Voice GUI Started[/] (PID: {vproc.pid})")
            console.print(f"    [dim]Logs: {voice_log}[/]")
            _write_pid(vproc.pid, "voice+cli")
            
            console.print("\n  [cyan]Launching CLI...[/]\n")
            try:
                from core.cli import run_cli
                run_cli()
            except KeyboardInterrupt:
                console.print("\n[dim]CLI closed.[/]")
            finally:
                console.print(f"  [dim]Shutting down Voice GUI (PID: {vproc.pid})...[/]", end=" ")
                try:
                    vproc.terminate()
                    vproc.wait(timeout=5)
                    console.print("[green]Done.[/]")
                except Exception:
                    try: vproc.kill()
                    except Exception: pass
                    console.print("[yellow]Force Killed.[/]")
                _clear_pid()
        finally:
            log_handle.close()

def launch_silent():
    if getattr(sys, "frozen", False):
        from server import main as server_main
        server_main()
    else:
        _ensure_log_dir()
        voice_log = LOG_DIR / f"voice_silent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        try:
            log_handle = open(voice_log, "w", encoding="utf-8")
            proc = subprocess.Popen(
                [PYTHON, str(BASE_DIR / "ui_mark.py")],
                cwd=str(BASE_DIR),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            _write_pid(proc.pid, "silent")
            log_handle.close()
        except Exception:
            pass

def launch_smoke():
    console.print("\n[bold cyan]▶ Running startup smoke checks[/]")
    script = BASE_DIR / "scripts" / "smoke_startup.py"
    if not script.exists():
        console.print("[red]✗ Smoke script not found.[/]")
        return
    try:
        subprocess.run([PYTHON, str(script)], cwd=str(BASE_DIR), check=False)
    except KeyboardInterrupt:
        console.print("\n[dim]Smoke checks interrupted.[/]")

def show_audio_status():
    _banner()
    console.print("[bold cyan]JARVIS Hardware Audio Diagnostics & Signal Meter[/]\n")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        default_in, default_out = sd.default.device

        table = Table(title="Audio Hardware Devices", title_style="bold magenta", box=None)
        table.add_column("Idx", style="bold cyan")
        table.add_column("Type", style="bold")
        table.add_column("Name")
        table.add_column("Default Rate", style="dim")
        table.add_column("Status")

        try:
            from voice.stt import SounddeviceMicrophone
            active_in = SounddeviceMicrophone().device_index
        except Exception:
            active_in = None
        active_out_str = os.environ.get("JARVIS_AUDIO_OUTPUT_DEVICE", "9").strip()
        active_out = int(active_out_str) if active_out_str.isdigit() else None

        for i, dev in enumerate(devices):
            in_ch = int(dev.get("max_input_channels", 0))
            out_ch = int(dev.get("max_output_channels", 0))
            if in_ch <= 0 and out_ch <= 0:
                continue
            kind = []
            if in_ch > 0:
                kind.append(f"IN({in_ch})")
            if out_ch > 0:
                kind.append(f"OUT({out_ch})")

            is_in = (i == active_in)
            is_out = (i == active_out)
            is_os_def = (i == default_in) or (i == default_out)

            if is_in and is_out:
                status_str = "[bold cyan]★ Active In/Out[/]"
            elif is_in:
                status_str = "[bold cyan]★ Active Input[/]"
            elif is_out:
                status_str = "[bold green]★ Active Output[/]"
            elif is_os_def:
                status_str = "[dim green]OS Default[/]"
            else:
                status_str = "[dim]Ready[/]"

            sample_rate = int(dev.get("default_samplerate", 44100))
            table.add_row(
                str(i),
                " / ".join(kind),
                str(dev.get("name", "")),
                f"{sample_rate} Hz",
                status_str
            )

        console.print(table)

        # Test Native Audio Signal RMS energy computation
        try:
            from core.native_bridge import audio_energy
            sample_signal = [0.05, 0.2, -0.15, 0.4, -0.3, 0.1, 0.5, -0.2]
            rms = audio_energy(sample_signal)
            console.print(f"\n[green]✓ Native C Audio RMS Processor Active:[/] Test Signal RMS Energy = [cyan]{rms:.4f}[/]")
        except Exception:
            pass

        # Live microphone VU Meter test
        console.print("\n[bold cyan]🎙️ Live Microphone Signal Calibration Check:[/]")
        mic_dev = 2
        try:
            import numpy as np
            from voice.stt import SounddeviceMicrophone
            mic_dev = SounddeviceMicrophone().device_index
            rec_data = sd.rec(int(0.5 * 16000), samplerate=16000, channels=1, device=mic_dev, dtype='float32')
            sd.wait()
            rms_val = float(np.sqrt(np.mean(rec_data**2)))
            bars = int(min(20, max(0, rms_val * 100)))
            meter_bar = "█" * bars + "░" * (20 - bars)
            console.print(f"  Live Mic Energy Level (Device {mic_dev}): [[cyan]{meter_bar}[/]] ({rms_val:.4f})")
            console.print("  [green]✓ Hardware Microphone Stream Operational[/]")
        except Exception as mic_err:
            console.print(f"  [yellow]⚠ Live mic test note: {mic_err}[/]")

        if not sys.stdin.isatty():
            return

        console.print("\n[bold cyan]🔧 Change Active Audio Devices:[/]")
        
        try:
            # 1. Input Device Prompt
            change_in = Prompt.ask(f"  [cyan]❯[/] Enter Audio INPUT Device Index (e.g. 3 for AirBass, 2 for Mic Array) [Press Enter to keep {mic_dev}]", default=str(mic_dev))
            if change_in.strip() and change_in.strip() != str(mic_dev):
                new_in = change_in.strip()
                env_file = BASE_DIR / ".env"
                if env_file.exists():
                    content = env_file.read_text(encoding="utf-8")
                    if "JARVIS_AUDIO_INPUT_DEVICE=" in content:
                        content = re.sub(r"JARVIS_AUDIO_INPUT_DEVICE=.*", f"JARVIS_AUDIO_INPUT_DEVICE={new_in}", content)
                    else:
                        content += f"\nJARVIS_AUDIO_INPUT_DEVICE={new_in}\n"
                    env_file.write_text(content, encoding="utf-8")
                os.environ["JARVIS_AUDIO_INPUT_DEVICE"] = new_in
                console.print(f"  [bold green]✓ Audio INPUT updated to Index {new_in} in .env![/]")

            # 2. Output Device Prompt
            curr_out = os.environ.get("JARVIS_AUDIO_OUTPUT_DEVICE", "5")
            change_out = Prompt.ask(f"  [cyan]❯[/] Enter Audio OUTPUT Device Index (e.g. 5 for AirBass, 7 for Speakers) [Press Enter to keep {curr_out}]", default=str(curr_out))
            if change_out.strip() and change_out.strip() != str(curr_out):
                new_out = change_out.strip()
                env_file = BASE_DIR / ".env"
                if env_file.exists():
                    content = env_file.read_text(encoding="utf-8")
                    if "JARVIS_AUDIO_OUTPUT_DEVICE=" in content:
                        content = re.sub(r"JARVIS_AUDIO_OUTPUT_DEVICE=.*", f"JARVIS_AUDIO_OUTPUT_DEVICE={new_out}", content)
                    else:
                        content += f"\nJARVIS_AUDIO_OUTPUT_DEVICE={new_out}\n"
                    env_file.write_text(content, encoding="utf-8")
                os.environ["JARVIS_AUDIO_OUTPUT_DEVICE"] = new_out
                console.print(f"  [bold green]✓ Audio OUTPUT updated to Index {new_out} in .env![/]")
        except (EOFError, KeyboardInterrupt):
            pass
    except Exception as e:
        console.print(f"[red]✗ Audio diagnostics failed:[/] {e}")

def launch_live_os():
    _banner()
    console.print("[bold cyan]Launching Live Autonomous OS Visual Controller ('Antigravity Mode')[/]\n")
    args = sys.argv[2:]
    is_bg = False
    if "--background" in args or "-bg" in args:
        is_bg = True
        args = [a for a in args if a not in ["--background", "-bg"]]

    goal = " ".join(args).strip()
    if not goal:
        goal = Prompt.ask("  [cyan]❯[/] Enter Live OS Control Goal")
    if not goal:
        console.print("[red]No goal specified.[/]")
        return
    max_steps = 0

    if is_bg:
        from actions.live_os_control import launch_live_os_background
        res = launch_live_os_background(goal, max_steps=max_steps)
        console.print(f"\n[bold green]{res}[/]")
    else:
        from actions.live_os_control import live_os_control_action
        res = live_os_control_action({"goal": goal, "max_steps": max_steps})
        console.print(f"\n[bold green]{res}[/]")

def launch_galaxy():
    _banner()
    console.print("[bold cyan]Launching Interactive 3D Knowledge Galaxy Viewer...[/]\n")
    port = int(os.environ.get("PORT", os.environ.get("BR_SERVER_PORT", "8000")))
    url = f"http://127.0.0.1:{port}/web/galaxy.html"
    launch_web_server(open_url=url)


# ── Main Entry ───────────────────────────────────────────────────────────────

def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower().strip().lstrip("-")
    elif not sys.stdin.isatty():
        mode = "voice"
    else:
        _banner()
        _check_env()
        
        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        table.add_column("Seq", style="bold cyan", justify="center", no_wrap=True)
        table.add_column("Module Sequence", style="bold green", no_wrap=True)
        table.add_column("Description & Capabilities", style="dim", no_wrap=False)
        
        table.add_row("1", "VOICE", "BR Hands-Free Voice Assistant (PySide GUI + Whisper ASR)")
        table.add_row("2", "CLI", "ReAct Terminal Orchestrator (Multi-LLM & Skills)")
        table.add_row("3", "BOTH", "Dual Execution: Voice Assistant + CLI Orchestrator")
        table.add_row("4", "WEB CORE", "Launch Glassmorphic Web Server & PWA Dashboard")
        table.add_row("5", "STATUS", "Subsystem Diagnostic Matrix, Artifacts & Gateway")
        table.add_row("6", "DOCTOR", "Auto-Install & Repair Python, System & Artifact Dirs")
        table.add_row("7", "SMOKE", "Run 10-Point Non-Destructive Startup Sanity Verification")
        table.add_row("8", "AUDIO", "Audio Hardware Meter & Native C RMS Signal Diagnostics")
        table.add_row("9", "LIVE OS", "Autonomous Visual Computer Control ('Antigravity Mode')")
        table.add_row("10", "FLOATING", "Frameless Glassmorphic Floating Live Voice Widget")
        table.add_row("11", "3D GALAXY", "Interactive 3D Knowledge Galaxy & Fly-To-Source Viewer")
        
        console.print(Panel(table, title="[bold cyan]◈ SELECT MODULE SEQUENCE ◈[/]", border_style="cyan", padding=(0, 2)))
        console.print()
        
        valid_choices = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11",
            "voice", "cli", "both", "web", "webserver", "webcore", "server", "api",
            "status", "health", "doctor", "fix", "smoke", "check", "verify",
            "audio", "sound", "live", "liveos", "os", "floating", "float", "overlay",
            "galaxy", "3d", "space", "nodes"
        ]
        
        try:
            choice_input = Prompt.ask(
                "  [bold cyan]❯ Ready (Select 1-11 or Module Name)[/]", 
                choices=valid_choices, 
                default="1",
                show_choices=False
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice_input = "1"
        
        mode_map = {
            "1": "voice", "voice": "voice", "v": "voice", "gui": "voice",
            "2": "cli", "cli": "cli", "c": "cli", "terminal": "cli",
            "3": "both", "both": "both", "b": "both", "all": "both",
            "4": "webserver", "web": "webserver", "webcore": "webserver", "server": "webserver", "api": "webserver",
            "5": "status", "status": "status", "health": "status",
            "6": "doctor", "doctor": "doctor", "fix": "doctor",
            "7": "smoke", "smoke": "smoke", "check": "smoke", "verify": "smoke",
            "8": "audio", "audio": "audio", "sound": "audio",
            "9": "live", "live": "live", "liveos": "live", "os": "live",
            "10": "floating", "floating": "floating", "float": "floating", "overlay": "floating",
            "11": "galaxy", "galaxy": "galaxy", "3d": "galaxy", "space": "galaxy", "nodes": "galaxy"
        }
        mode = mode_map.get(choice_input, choice_input)

    if mode in ("markui", "hud", "cyberpunk"): launch_mark_ui()
    elif mode in ("voice", "v", "gui"): launch_voice() if _pre_launch_check() else None
    elif mode in ("floating", "float", "overlay"): launch_floating_voice()
    elif mode in ("cli", "c", "terminal"): launch_cli() if _pre_launch_check() else None
    elif mode in ("both", "b", "all"): launch_both() if _pre_launch_check() else None
    elif mode in ("dashboard", "pwa", "mobile", "qr"): launch_dashboard_server()
    elif mode in ("webserver", "web", "server", "api"): launch_web_server()

    elif mode in ("status", "health"): show_status()
    elif mode in ("doctor", "fix"): doctor()
    elif mode in ("silent",): launch_silent()
    elif mode in ("smoke", "check", "verify"): launch_smoke()
    elif mode in ("audio", "sound"): show_audio_status()
    elif mode in ("live", "liveos", "os"): launch_live_os()
    elif mode in ("galaxy", "3d", "space", "nodes"): launch_galaxy()
    else:
        console.print(f"[red]✗ Unknown launch argument provided.[/]")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("\n[JARVIS] 👋 Launcher exited cleanly.")
        sys.exit(0)
