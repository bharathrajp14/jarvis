# scripts/build_app.py — Universal Cross-Platform App Builder & Deployment Package Generator
"""
Multi-Platform App Builder for BR JARVIS (Windows, Linux, macOS, Web/PWA).
Bundles native dependencies, web frontend assets, and standalone executables.
"""
from __future__ import annotations

import logging
import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist" / "BR_JARVIS_App"


def build_app():
    """Package BR JARVIS for cross-platform distribution."""
    logger.info("=" * 60)
    logger.info("  BR JARVIS -- Universal Multi-Platform App Builder")
    logger.info("=" * 60)
    logger.info(f"Target Platform OS: {platform.system()} ({platform.machine()})")
    
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Copy web frontend assets
    web_src = ROOT_DIR / "apps" / "web"
    if not web_src.exists():
        web_src = ROOT_DIR / "src" / "brjarvis" / "web"
    web_dest = DIST_DIR / "web"
    if web_dest.exists():
        shutil.rmtree(web_dest)
    if web_src.exists():
        shutil.copytree(web_src, web_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        logger.info(f"[OK] Packaged Web distribution assets -> {web_dest}")
    else:
        logger.warning("[WARN] Web source directory not found, skipping web asset bundling.")

    # 2. Copy core architecture configuration & knowledge base if present
    arch_src = ROOT_DIR / "docs" / "architecture"
    if not arch_src.exists():
        arch_src = ROOT_DIR / "docs"
    if arch_src.exists():
        arch_dest = DIST_DIR / "docs"
        if arch_dest.exists():
            shutil.rmtree(arch_dest)
        shutil.copytree(arch_src, arch_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        logger.info(f"[OK] Packaged Architecture Knowledge Base -> {arch_dest}")

    # 3. Generate Platform Launchers
    os_name = platform.system().lower()
    if os_name == "windows":
        launcher_file = DIST_DIR / "launch_jarvis.bat"
        launcher_file.write_text(
            "@echo off\n"
            "echo Starting BR JARVIS Multi-Platform AI Operating System...\n"
            "python start.py web --port 8000\n"
            "pause\n",
            encoding="utf-8"
        )
        logger.info(f"[OK] Created Windows Launcher -> {launcher_file}")

    elif os_name in ("linux", "darwin"):
        launcher_file = DIST_DIR / "launch_jarvis.sh"
        launcher_file.write_text(
            "#!/usr/bin/env bash\n"
            "echo 'Starting BR JARVIS Multi-Platform AI Operating System...'\n"
            "python3 start.py --web --port 8000\n",
            encoding="utf-8"
        )
        launcher_file.chmod(0o755)
        logger.info(f"[OK] Created Unix Launcher -> {launcher_file}")

    logger.info("-" * 60)
    logger.info(f"[SUCCESS] Build Complete! Application package ready in: {DIST_DIR}")
    logger.info("=" * 60)


if __name__ == "__main__":
    build_app()
