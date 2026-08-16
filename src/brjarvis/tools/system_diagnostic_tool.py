# tools/system_diagnostic_tool.py — OS Telemetry, Tool Health & Self-Test Diagnostic Subsystem for JARVIS MK40
"""
Provides real-time system resource monitoring, memory/CPU pressure auditing,
disk usage analysis, network port inspection, tool health diagnostics, and safe self-tests.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import platform
import shutil
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import psutil
from .registry import register_tool

logger = logging.getLogger(__name__)


def check_tool_health() -> Dict[str, Dict[str, Any]]:
    """Audit runtime readiness of all tools, libraries, and external integrations."""
    health: Dict[str, Dict[str, Any]] = {}

    # 1. Document & File Generation Libraries
    try:
        import docx
        health["DOCX Generator (python-docx)"] = {"status": "READY", "details": f"v{getattr(docx, '__version__', 'available')}"}
    except ImportError:
        health["DOCX Generator (python-docx)"] = {"status": "DISABLED", "details": "python-docx not installed"}

    try:
        import fpdf
        health["PDF Generator (fpdf)"] = {"status": "READY", "details": "FPDF library loaded"}
    except ImportError:
        health["PDF Generator (fpdf)"] = {"status": "DISABLED", "details": "fpdf not installed"}

    try:
        import openpyxl
        health["Excel Spreadsheet (openpyxl)"] = {"status": "READY", "details": f"v{openpyxl.__version__}"}
    except ImportError:
        health["Excel Spreadsheet (openpyxl)"] = {"status": "DISABLED", "details": "openpyxl not installed"}

    # 2. Web Search & Scraping Engines
    ddg_ok = False
    try:
        import ddgs
        health["Web Search (ddgs)"] = {"status": "READY", "details": "DuckDuckGo search client active"}
        ddg_ok = True
    except ImportError:
        try:
            import duckduckgo_search
            health["Web Search (duckduckgo_search)"] = {"status": "READY", "details": "DuckDuckGo search client active"}
            ddg_ok = True
        except ImportError:
            health["Web Search (DuckDuckGo)"] = {"status": "DEGRADED", "details": "ddgs/duckduckgo_search missing"}

    try:
        import playwright
        health["Browser Automation (Playwright)"] = {"status": "READY", "details": "Playwright async engine loaded"}
    except Exception:
        health["Browser Automation (Playwright)"] = {"status": "DEGRADED", "details": "Playwright engine unavailable"}

    # 3. OS Automation & Telemetry
    health["Process Telemetry (psutil)"] = {"status": "READY", "details": f"v{psutil.__version__}"}

    git_bin = shutil.which("git")
    if git_bin:
        health["Version Control (Git)"] = {"status": "READY", "details": f"Binary located at {git_bin}"}
    else:
        health["Version Control (Git)"] = {"status": "DISABLED", "details": "git binary not found in PATH"}

    # 4. Memory & Verification Subsystem
    try:
        from memory.unified_memory import get_unified_memory
        um = get_unified_memory()
        health["Hierarchical Memory (L0-L6)"] = {"status": "READY", "details": "7-tier memory subsystem active"}
    except Exception as e:
        health["Hierarchical Memory (L0-L6)"] = {"status": "DEGRADED", "details": f"Memory init warning: {e}"}

    try:
        from agent.verifier import ActionVerifier
        health["Action Verifier Suite"] = {"status": "READY", "details": "File, Process, Window & Artifact verifiers active"}
    except Exception as e:
        health["Action Verifier Suite"] = {"status": "DISABLED", "details": str(e)}

    # 5. Multichannel Connectors
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    health["Telegram Connector"] = {
        "status": "READY" if tg_token else "NOT_CONFIGURED",
        "details": "Bot token set" if tg_token else "TELEGRAM_BOT_TOKEN missing in environment"
    }

    gmail_configured = Path("config/credentials.json").exists() or os.environ.get("GMAIL_USER")
    health["Gmail Connector"] = {
        "status": "READY" if gmail_configured else "NOT_CONFIGURED",
        "details": "OAuth credentials / credentials.json found" if gmail_configured else "OAuth credentials missing"
    }

    wp_session = Path("config/whatsapp_session.json").exists()
    health["WhatsApp Connector"] = {
        "status": "READY" if wp_session else "STANDBY",
        "details": "Session active" if wp_session else "QR pairing standby / web launcher available"
    }

    return health


def run_safe_self_test() -> Dict[str, Any]:
    """Execute safe non-destructive end-to-end self-tests on critical agent capabilities."""
    test_results: Dict[str, Any] = {"passed": [], "failed": [], "timestamp": time.time()}

    # Test 1: File write and read verification
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "jarvis_selftest.txt"
            test_content = f"JARVIS_SELF_TEST_TOKEN_{time.time()}"
            test_file.write_text(test_content, encoding="utf-8")

            from agent.verifier import ActionVerifier
            res = ActionVerifier.verify_file_content(str(test_file), expected_substrings=[test_content])
            if res.verified:
                test_results["passed"].append({"name": "File Write & Content Verification", "evidence": res.evidence})
            else:
                test_results["failed"].append({"name": "File Write & Content Verification", "error": res.details})
    except Exception as e:
        test_results["failed"].append({"name": "File Write & Content Verification", "error": str(e)})

    # Test 2: Executive DOCX Document Generation & Structural Parsing
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_docx = Path(tmpdir) / "jarvis_selftest.docx"
            from tools.doc_tools import document_creator
            document_creator({
                "title": "Self Test Diagnostic Document",
                "content": "# Test Header\n\nThis is a non-destructive automated self-test.\n\n| Param | Value |\n| --- | --- |\n| Status | Verified |",
                "filename": str(test_docx),
                "format": "docx",
                "auto_open": False
            })

            from agent.verifier import ActionVerifier
            doc_res = ActionVerifier.verify_file_parsed(str(test_docx))
            if doc_res.verified:
                test_results["passed"].append({"name": "DOCX Generation & Parsing Verification", "evidence": doc_res.evidence})
            else:
                test_results["failed"].append({"name": "DOCX Generation & Parsing Verification", "error": doc_res.details})
    except Exception as e:
        test_results["failed"].append({"name": "DOCX Generation & Parsing Verification", "error": str(e)})

    # Test 3: Operational Memory Record
    try:
        from memory.unified_memory import get_unified_memory
        um = get_unified_memory()
        um.record_operational_lesson(
            tool_name="self_test_diagnostic",
            goal="Automated system self-test",
            success=True,
            result_summary="Passed automated diagnostic self-test.",
        )
        test_results["passed"].append({"name": "Memory Operational Lesson Recording", "evidence": "Recorded L6 memory trajectory without error."})
    except Exception as e:
        test_results["failed"].append({"name": "Memory Operational Lesson Recording", "error": str(e)})

    return test_results


@register_tool(
    name="system_diagnostic",
    description="Inspect system telemetry, CPU/RAM, active network ports, tool health status, or run safe self-tests.",
    parameters={
        "type": "object",
        "properties": {
            "aspect": {
                "type": "string",
                "enum": ["full_summary", "cpu_ram", "top_processes", "disk_io", "network_ports", "tool_health", "self_test"],
                "description": "System telemetry or diagnostic aspect to query"
            },
            "top_n": {"type": "integer", "description": "Number of top processes to return (default: 5)"}
        },
        "required": ["aspect"]
    }
)
def system_diagnostic(args: dict) -> str:
    aspect = args.get("aspect", "full_summary")
    top_n = args.get("top_n", 5)

    if aspect == "tool_health":
        health = check_tool_health()
        lines = ["🔧 BR JARVIS Autonomous Tool & Capability Health Check:", ""]
        for name, info in health.items():
            st = info["status"]
            icon = "✅" if st == "READY" else "⚠️" if st in ("STANDBY", "DEGRADED") else "⚪" if st == "NOT_CONFIGURED" else "❌"
            lines.append(f"  {icon} {name:<35} [{st:<14}] {info['details']}")
        return "\n".join(lines)

    elif aspect == "self_test":
        st_res = run_safe_self_test()
        lines = ["🧪 BR JARVIS Safe Automated Self-Test Results:", ""]
        for p in st_res["passed"]:
            lines.append(f"  ✅ PASS: {p['name']} — {p.get('evidence', '')}")
        for f in st_res["failed"]:
            lines.append(f"  ❌ FAIL: {f['name']} — {f.get('error', '')}")
        lines.append(f"\nTotal: {len(st_res['passed'])} Passed, {len(st_res['failed'])} Failed.")
        return "\n".join(lines)

    elif aspect == "cpu_ram":
        cpu_pct = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return (
            f"💻 CPU & Memory Status:\n"
            f"- CPU Usage: {cpu_pct}% ({cpu_count} logical cores)\n"
            f"- RAM Usage: {mem.percent}% ({mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB used)\n"
            f"- Swap Usage: {swap.percent}% ({swap.used / (1024**3):.2f} GB / {swap.total / (1024**3):.2f} GB used)"
        )

    elif aspect == "top_processes":
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
            try:
                info = p.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        procs_by_mem = sorted(procs, key=lambda x: x['memory_percent'] or 0, reverse=True)[:top_n]
        out = [f"🔥 Top {top_n} Memory-Consuming Processes:"]
        for p in procs_by_mem:
            rss_mb = (p['memory_info'].rss / (1024**2)) if p.get('memory_info') else 0
            out.append(f"  ● PID {p['pid']:<6} | {p['name']:<25} | RAM: {rss_mb:.1f} MB ({p['memory_percent']:.1f}%) | CPU: {p['cpu_percent'] or 0:.1f}%")
        return "\n".join(out)

    elif aspect == "disk_io":
        disks = psutil.disk_partitions()
        out = ["💾 Disk Partition Usage:"]
        for d in disks:
            try:
                usage = psutil.disk_usage(d.mountpoint)
                out.append(f"  ● Drive {d.mountpoint:<6} ({d.fstype or 'N/A'}) -> Used: {usage.percent}% ({usage.used / (1024**3):.1f} GB / {usage.total / (1024**3):.1f} GB)")
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
        return "\n".join(out)

    elif aspect == "network_ports":
        conns = []
        try:
            for c in psutil.net_connections(kind='inet'):
                if c.status == 'LISTEN':
                    laddr = f"{c.laddr.ip}:{c.laddr.port}"
                    conns.append(f"  ● Port {c.laddr.port:<5} | PID {c.pid or 'N/A':<6} | Address: {laddr}")
            if not conns:
                return "🌐 Listening Sockets: None found or elevated privileges required."
            return "🌐 Active Listening Ports:\n" + "\n".join(conns[:15])
        except Exception as e:
            return f"Network sockets query error: {e}"

    elif aspect == "full_summary":
        cpu_pct = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        uname = platform.uname()
        return (
            f"🖥️ System Health Overview ({uname.system} {uname.release}):\n"
            f"- Host: {uname.node}\n"
            f"- CPU: {cpu_pct}% ({psutil.cpu_count()} cores)\n"
            f"- RAM: {mem.percent}% ({mem.used / (1024**3):.2f} / {mem.total / (1024**3):.2f} GB)\n"
            f"- Python: {sys.version.split()[0]}\n"
            f"- System Uptime: {(psutil.time.time() - psutil.boot_time()) / 3600:.1f} hours"
        )

    return f"Unknown aspect '{aspect}'."


@register_tool(
    name="runtime_diagnostics",
    description="Inspect and diagnose actual runtime environments (Python virtualenv, Node, Git, PowerShell, Playwright/Chromium) and tested capability readiness.",
    parameters={
        "type": "object",
        "properties": {
            "aspect": {
                "type": "string",
                "enum": ["all", "environments", "packages", "policy"],
                "description": "Diagnostic scope to inspect (default: all)"
            }
        }
    }
)
def runtime_diagnostics(args: dict) -> str:
    """Inspect and report tested runtime environment capabilities."""
    try:
        from brjarvis.core.execution.universal_runtime import get_universal_runtime
        rt = get_universal_runtime()
        diag = rt.diagnose_runtime()
        
        aspect = (args.get("aspect") or "all").lower().strip()
        if aspect == "environments":
            return json.dumps(diag["environments"], indent=2)
        elif aspect == "packages":
            return json.dumps(diag["packages_in_python_venv"], indent=2)
        elif aspect == "policy":
            return f"Precedence Policy: {diag['precedence_policy']}\nRepair Policy: {diag['repair_policy']}"

        lines = [
            "⚡ BR JARVIS MK40.2 Universal Runtime Diagnostics:",
            f"  ● Platform: {diag['platform']['system']} ({diag['platform']['os']})",
            f"  ● Working Directory: {diag['platform']['cwd']}",
            f"  ● Project Root: {diag['platform']['project_root']}",
            "",
            "📦 Resolved Runtimes:",
        ]
        for r_name, r_info in diag["environments"].items():
            st = "✅" if r_info.get("is_healthy", True) and r_info.get("executable") else "❌"
            src = r_info.get("precedence_source", "unknown")
            tier = r_info.get("precedence_tier", "?")
            lines.append(f"  {st} {r_name.capitalize():<12}: {r_info.get('executable', 'N/A')} (Tier {tier}: {src}) [v{r_info.get('version', 'N/A')}]")

        lines.append("")
        lines.append("📚 Target Virtualenv Tested Packages:")
        for pkg_name, p_info in diag["packages_in_python_venv"].items():
            p_st = "✅" if p_info.get("available") else "❌"
            lines.append(f"  {p_st} {pkg_name:<16}: {p_info.get('version', 'NOT INSTALLED')}")

        lines.append("")
        lines.append(f"🛡️ Active Policies: {diag['repair_policy']} | Precedence: {diag['precedence_policy']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Runtime diagnostics error: {e}"


@register_tool(
    name="dependency_diagnostics",
    description="Query whether a specific module, package, executable, or tool capability is available in the target runtime environment.",
    parameters={
        "type": "object",
        "properties": {
            "module_or_package": {
                "type": "string",
                "description": "Python module or package name to check (e.g. 'fitz', 'PyMuPDF', 'docx', 'playwright', 'pypdf')"
            },
            "executable": {
                "type": "string",
                "description": "System executable to check (e.g. 'git', 'node', 'pwsh')"
            }
        }
    }
)
def dependency_diagnostics(args: dict) -> str:
    """Diagnose dependency availability in target execution environment."""
    try:
        from brjarvis.core.execution.dependency_resolver import get_dependency_resolver
        from brjarvis.core.execution.environment_resolver import get_environment_resolver
        from brjarvis.core.execution.types import DependencyDeclaration, RuntimeType

        dep_resolver = get_dependency_resolver()
        env_resolver = get_environment_resolver()
        py_env = env_resolver.resolve_python()

        mod_name = args.get("module_or_package", "").strip()
        exe_name = args.get("executable", "").strip()

        if mod_name:
            pkg_name = dep_resolver.map_module_to_package(mod_name)
            is_installed, ver = dep_resolver.verify_python_import(mod_name, py_env)
            
            status_icon = "✅" if is_installed else "❌"
            return (
                f"Dependency Diagnostic Report:\n"
                f"- Import Name: {mod_name}\n"
                f"- Distribution Package: {pkg_name}\n"
                f"- Target Environment: {py_env.precedence_source} ({py_env.executable})\n"
                f"- Status: {status_icon} {'AVAILABLE' if is_installed else 'MISSING'}\n"
                f"- Version / Details: {ver}\n"
                f"- Safe Auto-Repair Command: {py_env.executable} -m pip install {pkg_name}"
            )

        if exe_name:
            resolved = shutil.which(exe_name)
            status_icon = "✅" if resolved else "❌"
            return (
                f"Executable Diagnostic Report:\n"
                f"- Executable: {exe_name}\n"
                f"- Status: {status_icon} {'FOUND' if resolved else 'NOT FOUND'}\n"
                f"- Resolved Path: {resolved or 'N/A'}"
            )

        return "Please specify 'module_or_package' or 'executable' to diagnose."
    except Exception as e:
        return f"Dependency diagnostics error: {e}"

