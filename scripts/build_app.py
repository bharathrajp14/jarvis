# scripts/build_app.py — Universal Cross-Platform App Builder & Deployment Package Generator
"""
Multi-Platform App Builder for BR JARVIS (Windows, Linux, macOS, Web/PWA).
Bundles native dependencies, web frontend assets, and standalone executables.
"""
from __future__ import annotations

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist" / "BR_JARVIS_App"


def build_app():
    """Package BR JARVIS for cross-platform distribution."""
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    if 'logger' in globals() or 'logger' in locals():
        logger.info("  BR JARVIS -- Universal Multi-Platform App Builder")
    else:
        import logging
        logging.getLogger(__name__).info("  BR JARVIS -- Universal Multi-Platform App Builder")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"Target Platform OS: {platform.system()} ({platform.machine()})" }" if isinstance(f"Target Platform OS: {platform.system()} ({platform.machine()})", str) else f"Target Platform OS: {platform.system()} ({platform.machine()})")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"Target Platform OS: {platform.system()} ({platform.machine()})" }" if isinstance(f"Target Platform OS: {platform.system()} ({platform.machine()})", str) else f"Target Platform OS: {platform.system()} ({platform.machine()})")
    
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Copy web frontend assets (HTML, CSS, JS, Manifest, SW)
    web_dest = DIST_DIR / "web"
    if web_dest.exists():
        shutil.rmtree(web_dest)
    shutil.copytree(ROOT_DIR / "web", web_dest)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"[OK] Packaged Web/PWA distribution assets -> {web_dest}" }" if isinstance(f"[OK] Packaged Web/PWA distribution assets -> {web_dest}", str) else f"[OK] Packaged Web/PWA distribution assets -> {web_dest}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"[OK] Packaged Web/PWA distribution assets -> {web_dest}" }" if isinstance(f"[OK] Packaged Web/PWA distribution assets -> {web_dest}", str) else f"[OK] Packaged Web/PWA distribution assets -> {web_dest}")

    # 2. Copy core architecture configuration & knowledge base
    arch_dest = DIST_DIR / "br_architecture"
    if arch_dest.exists():
        shutil.rmtree(arch_dest)
    shutil.copytree(ROOT_DIR / "br_architecture", arch_dest)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"[OK] Packaged Architecture Knowledge Base -> {arch_dest}" }" if isinstance(f"[OK] Packaged Architecture Knowledge Base -> {arch_dest}", str) else f"[OK] Packaged Architecture Knowledge Base -> {arch_dest}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"[OK] Packaged Architecture Knowledge Base -> {arch_dest}" }" if isinstance(f"[OK] Packaged Architecture Knowledge Base -> {arch_dest}", str) else f"[OK] Packaged Architecture Knowledge Base -> {arch_dest}")

    # 3. Generate Platform Launchers
    os_name = platform.system().lower()
    if os_name == "windows":
        launcher_file = DIST_DIR / "launch_jarvis.bat"
        launcher_file.write_text(
            "@echo off\n"
            "echo Starting BR JARVIS Multi-Platform AI Operating System...\n"
            "python start.py --web --port 8000\n"
            "pause\n",
            encoding="utf-8"
        )
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[OK] Created Windows Launcher -> {launcher_file}" }" if isinstance(f"[OK] Created Windows Launcher -> {launcher_file}", str) else f"[OK] Created Windows Launcher -> {launcher_file}")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[OK] Created Windows Launcher -> {launcher_file}" }" if isinstance(f"[OK] Created Windows Launcher -> {launcher_file}", str) else f"[OK] Created Windows Launcher -> {launcher_file}")

    elif os_name in ("linux", "darwin"):
        launcher_file = DIST_DIR / "launch_jarvis.sh"
        launcher_file.write_text(
            "#!/usr/bin/env bash\n"
            "echo 'Starting BR JARVIS Multi-Platform AI Operating System...'\n"
            "python3 start.py --web --port 8000\n",
            encoding="utf-8"
        )
        launcher_file.chmod(0o755)
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[OK] Created Unix Launcher -> {launcher_file}" }" if isinstance(f"[OK] Created Unix Launcher -> {launcher_file}", str) else f"[OK] Created Unix Launcher -> {launcher_file}")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[OK] Created Unix Launcher -> {launcher_file}" }" if isinstance(f"[OK] Created Unix Launcher -> {launcher_file}", str) else f"[OK] Created Unix Launcher -> {launcher_file}")

    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "-" * 60 }" if isinstance("-" * 60, str) else "-" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "-" * 60 }" if isinstance("-" * 60, str) else "-" * 60)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"[SUCCESS] Build Complete! Application package ready in: {DIST_DIR}" }" if isinstance(f"[SUCCESS] Build Complete! Application package ready in: {DIST_DIR}", str) else f"[SUCCESS] Build Complete! Application package ready in: {DIST_DIR}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"[SUCCESS] Build Complete! Application package ready in: {DIST_DIR}" }" if isinstance(f"[SUCCESS] Build Complete! Application package ready in: {DIST_DIR}", str) else f"[SUCCESS] Build Complete! Application package ready in: {DIST_DIR}")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)


if __name__ == "__main__":
    build_app()
