# tests/test_plugin_manager.py — Unit Tests for Priority 8 Plugin Runtime Platform
from __future__ import annotations

import json
import pytest
from pathlib import Path
from plugins.plugin_manager import PluginManager, PluginStatus, get_plugin_manager


def test_plugin_manager_discovery(tmp_path):
    # Create a dummy plugin directory
    plugin_dir = tmp_path / "dummy_plugin"
    plugin_dir.mkdir()

    meta = {
        "name": "Dummy Plugin",
        "version": "2.0.0",
        "description": "Test dummy plugin",
        "entry_point": "main.py"
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(meta), encoding="utf-8")
    (plugin_dir / "main.py").write_text("def on_load(runtime):\n    pass\n", encoding="utf-8")

    mgr = PluginManager()
    loaded_meta = mgr.load_plugin_folder(plugin_dir)

    assert loaded_meta is not None
    assert loaded_meta.name == "Dummy Plugin"
    assert loaded_meta.status == PluginStatus.ACTIVE
