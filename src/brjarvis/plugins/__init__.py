# plugins/__init__.py — JARVIS MK37 Plugin Subsystem Package Interface
from __future__ import annotations

from .plugin_manager import PluginManager, PluginMetadata, PluginStatus, get_plugin_manager


def load_custom_plugins() -> list[dict]:
    """Backward compatibility wrapper for legacy plugin loader."""
    mgr = get_plugin_manager()
    plugins = mgr.discover_and_load_plugins()
    return [
        {
            "name": p.name,
            "version": p.version,
            "description": p.description,
            "author": p.author,
        }
        for p in plugins
    ]


__all__ = [
    "PluginManager",
    "get_plugin_manager",
    "PluginMetadata",
    "PluginStatus",
    "load_custom_plugins",
]
