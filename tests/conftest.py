# tests/conftest.py — Global Pytest Configuration and Environment Setup
from __future__ import annotations

import sys
from pathlib import Path
import pytest

# Add src, apps, and project root to sys.path
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
_APPS_WEB = _ROOT / "apps" / "web"

for p in [str(_SRC), str(_APPS_WEB), str(_ROOT)]:
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

import brjarvis

# Complete mapping of top-level legacy namespaces to canonical brjarvis.* packages
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
    "context": "brjarvis.context",
    "computer": "brjarvis.computer",
    "reasoning": "brjarvis.reasoning",
    "events": "brjarvis.events",
    "history": "brjarvis.history",
    "native": "brjarvis.native",
    "api": "brjarvis.apps.web.api",
    "plugins": "brjarvis.plugins",
    "screen_server": "brjarvis.screen_server",
    "multi_agent": "brjarvis.multi_agent",
    "redteam": "brjarvis.guardian.redteam",
    "evolution": "brjarvis.evolution",
}

import importlib
for leg, can in _ALIASES.items():
    try:
        mod = importlib.import_module(can)
        sys.modules[leg] = mod
    except Exception:
        pass


def _sync_module_aliases():
    """Ensure all loaded canonical brjarvis.* submodules are mirrored to legacy names."""
    for mod_name, mod_obj in list(sys.modules.items()):
        if mod_obj is None:
            continue
        if mod_name.startswith("brjarvis."):
            for leg, can in _ALIASES.items():
                if mod_name == can or mod_name.startswith(can + "."):
                    suffix = mod_name[len(can):]
                    legacy_name = leg + suffix
                    if legacy_name not in sys.modules or sys.modules[legacy_name] is not mod_obj:
                        sys.modules[legacy_name] = mod_obj
        else:
            for leg, can in _ALIASES.items():
                if mod_name == leg or mod_name.startswith(leg + "."):
                    suffix = mod_name[len(leg):]
                    can_name = can + suffix
                    if can_name not in sys.modules or sys.modules[can_name] is not mod_obj:
                        sys.modules[can_name] = mod_obj


_sync_module_aliases()


@pytest.fixture(autouse=True)
def _auto_sync_aliases_fixture():
    """Run before and after each test to keep legacy and canonical sys.modules synchronized."""
    _sync_module_aliases()
    yield
    _sync_module_aliases()
