# tests/conftest.py — Global Pytest Configuration and Environment Setup
from __future__ import annotations

import sys
from pathlib import Path

# Add src and apps directory with highest priority
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
_PKG = _SRC / "brjarvis"
_APPS_WEB = _ROOT / "apps" / "web"

for p in [str(_SRC), str(_PKG), str(_APPS_WEB), str(_ROOT)]:
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

import brjarvis

# Pre-register top-level legacy aliases in sys.modules for pytest compatibility
_ALIASES = {
    "core": "brjarvis.core",
    "career": "brjarvis.career",
    "agent": "brjarvis.agent",
    "memory": "brjarvis.memory",
    "tools": "brjarvis.tools",
    "actions": "brjarvis.actions",
    "connectors": "brjarvis.connectors",
    "voice": "brjarvis.voice",
    "vision": "brjarvis.vision",
    "ui": "brjarvis.ui",
    "desktop": "brjarvis.desktop",
    "skills": "brjarvis.skills",
    "orchestrator": "brjarvis.orchestrator",
    "router": "brjarvis.router",
    "gateway": "brjarvis.gateway",
    "guardian": "brjarvis.guardian",
    "security": "brjarvis.security",
    "workflow": "brjarvis.workflow",
    "backends": "brjarvis.integrations.backends",
    "mobile": "brjarvis.integrations.mobile",
    "api": "brjarvis.apps.web.api",
    "plugins": "brjarvis.plugins",
    "screen_server": "brjarvis.screen_server",
    "multi_agent": "brjarvis.multi_agent",
}

import importlib
for leg, can in _ALIASES.items():
    try:
        mod = importlib.import_module(can)
        sys.modules[leg] = mod
    except Exception:
        pass

# Automatically alias all loaded canonical submodules to legacy names
for mod_name, mod_obj in list(sys.modules.items()):
    if mod_name.startswith("brjarvis."):
        for leg, can in _ALIASES.items():
            if mod_name == can or mod_name.startswith(can + "."):
                suffix = mod_name[len(can):]
                legacy_name = leg + suffix
                sys.modules.setdefault(legacy_name, mod_obj)
