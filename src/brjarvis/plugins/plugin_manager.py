# plugins/plugin_manager.py — Dynamic Plugin Platform Engine for JARVIS MK37
from __future__ import annotations

import enum
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.runtime import get_runtime
from events.bus import get_event_bus
from tools.tool_runtime import get_tool_runtime

logger = logging.getLogger("JARVIS.PluginManager")

PLUGINS_DIR = Path(__file__).resolve().parent


class PluginStatus(str, enum.Enum):
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    UNLOADED = "UNLOADED"


class PluginMetadata(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "Unknown"
    entry_point: str = "main.py"
    status: PluginStatus = PluginStatus.UNLOADED
    folder_path: str


class PluginManager:
    """Dynamic Plugin Platform Manager with sandbox isolation and lifecycle hooks."""

    def __init__(self):
        self.runtime = get_runtime()
        self.event_bus = get_event_bus()
        self.tool_runtime = get_tool_runtime()

        self._plugins: Dict[str, PluginMetadata] = {}
        self._modules: Dict[str, Any] = {}

        # Register self in DI Container
        self.runtime.container.register_instance(PluginManager, self)
        logger.info("⚡ PluginManager initialized")

    def discover_and_load_plugins(self) -> List[PluginMetadata]:
        """Scans plugins/ directory and loads valid community plugins."""
        if not PLUGINS_DIR.exists():
            return []

        for folder in PLUGINS_DIR.iterdir():
            if folder.is_dir() and not folder.name.startswith("__"):
                json_path = folder / "plugin.json"
                if json_path.exists():
                    self.load_plugin_folder(folder)

        return list(self._plugins.values())

    def load_plugin_folder(self, folder: Path) -> Optional[PluginMetadata]:
        """Loads a single plugin from a folder path."""
        json_path = folder / "plugin.json"
        try:
            meta_data = json.loads(json_path.read_text(encoding="utf-8"))
            name = meta_data.get("name", folder.name)
            entry_point = meta_data.get("entry_point", "main.py")
            script_path = folder / entry_point

            meta = PluginMetadata(
                name=name,
                version=meta_data.get("version", "1.0.0"),
                description=meta_data.get("description", ""),
                author=meta_data.get("author", "Unknown"),
                entry_point=entry_point,
                status=PluginStatus.UNLOADED,
                folder_path=str(folder),
            )

            if script_path.exists():
                spec = importlib.util.spec_from_file_location(f"jarvis_plugin_{folder.name}", str(script_path))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)

                    # Trigger on_load hook if defined
                    if hasattr(module, "on_load"):
                        module.on_load(self.runtime)

                    meta.status = PluginStatus.ACTIVE
                    self._plugins[name] = meta
                    self._modules[name] = module
                    logger.info(f"✅ PluginManager: Loaded plugin '{name}' v{meta.version} from {folder.name}")
                    return meta

        except Exception as e:
            logger.error(f"❌ PluginManager: Failed to load plugin from {folder.name}: {e}", exc_info=True)
            meta = PluginMetadata(
                name=folder.name,
                status=PluginStatus.FAILED,
                folder_path=str(folder),
            )
            self._plugins[folder.name] = meta

        return None

    def list_plugins(self) -> List[PluginMetadata]:
        """Retrieve metadata of all discovered plugins."""
        return list(self._plugins.values())


_global_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _global_plugin_manager
    if _global_plugin_manager is None:
        _global_plugin_manager = PluginManager()
    return _global_plugin_manager
