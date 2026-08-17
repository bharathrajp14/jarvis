# connectors/hub.py — BR JARVIS Connector Hub (Central Registry & Router)
"""
ConnectorHub: Auto-discovers, loads, and routes calls to all installed connector plugins.

Features:
  - Auto-discovers all connectors in the connectors/ directory
  - Routes "connector_id/tool_name" calls to the correct plugin
  - Status dashboard: shows which connectors are active vs. needing config
  - Registers all connector tools into the main JARVIS tool registry
  - Handles errors gracefully (one bad connector never crashes JARVIS)
"""
from __future__ import annotations

import importlib
import json
import logging
import pkgutil
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.ConnectorHub")


class ConnectorHub:
    """
    Central connector registry and dispatcher for BR JARVIS.

    Usage:
        hub = get_hub()
        result = hub.call("wikipedia", "search", {"query": "neural networks"})
        status = hub.status_report()
    """

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._load_errors: Dict[str, str] = {}
        self._discover_connectors()

    # ── Discovery ─────────────────────────────────────────────────────────────

    def _discover_connectors(self) -> None:
        """
        Auto-discover all BaseConnector subclasses in the connectors/ package.
        Each module that defines a class inheriting BaseConnector is auto-loaded.
        """
        connectors_pkg_dir = Path(__file__).resolve().parent
        skip_files = {"__init__", "base", "hub"}

        for finder, module_name, _ in pkgutil.iter_modules([str(connectors_pkg_dir)]):
            if module_name in skip_files:
                continue
            try:
                full_name = f"connectors.{module_name}"
                mod = importlib.import_module(full_name)

                # Find all BaseConnector subclasses in the module
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BaseConnector)
                        and obj is not BaseConnector
                    ):
                        try:
                            instance = obj()
                            self._connectors[instance.connector_id] = instance
                            status = "✅" if instance.is_configured else "⚠️ (needs config)"
                            logger.info(
                                "ConnectorHub: Loaded '%s' %s",
                                instance.display_name, status
                            )
                        except Exception as e:
                            logger.warning(
                                "ConnectorHub: Could not instantiate %s: %s", attr_name, e
                            )
            except Exception as e:
                self._load_errors[module_name] = str(e)
                logger.debug("ConnectorHub: Skipping '%s': %s", module_name, e)

        active = sum(1 for c in self._connectors.values() if c.is_configured)
        logger.info(
            "ConnectorHub: %d connectors loaded (%d active, %d need config)",
            len(self._connectors), active, len(self._connectors) - active
        )

    # ── Routing ───────────────────────────────────────────────────────────────

    def call(
        self,
        connector_id: str,
        tool_name: str,
        args: Dict[str, Any] | None = None,
    ) -> str:
        """
        Route a tool call to a specific connector.

        Args:
            connector_id: The connector's ID (e.g. 'github', 'wikipedia')
            tool_name: The tool to call (e.g. 'search', 'get_file')
            args: Tool arguments dict

        Returns:
            Result as a string (JSON-formatted if dict/list).
        """
        args = args or {}

        connector = self._connectors.get(connector_id)
        if not connector:
            available = list(self._connectors.keys())
            return (
                f"❌ Connector '{connector_id}' not found.\n"
                f"Available connectors: {available}"
            )

        if not connector.is_configured:
            return (
                f"⚠️ Connector '{connector.display_name}' needs configuration.\n"
                f"Setup guide: {connector.auth_hint}"
            )

        try:
            result = connector.call_tool(tool_name, args)
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2, ensure_ascii=False)
            return str(result)
        except Exception as e:
            logger.error(
                "ConnectorHub: Error in %s/%s: %s",
                connector_id, tool_name, e, exc_info=True
            )
            return f"❌ Error in connector '{connector_id}/{tool_name}': {e}"

    # ── Registry Queries ──────────────────────────────────────────────────────

    def list_connectors(self) -> List[Dict[str, Any]]:
        """Return a list of all registered connectors with their status."""
        results = []
        for cid, conn in self._connectors.items():
            results.append({
                "id": cid,
                "name": conn.display_name,
                "description": conn.description,
                "icon": conn.icon,
                "configured": conn.is_configured,
                "requires_auth": conn.requires_auth,
                "auth_hint": conn.auth_hint if not conn.is_configured else "",
                "tools": [t.to_dict() for t in conn.list_tools()],
            })
        return results

    def list_all_tools(self) -> List[Dict[str, Any]]:
        """Return ALL tools from ALL configured connectors (flat list)."""
        tools = []
        for cid, conn in self._connectors.items():
            if not conn.is_configured:
                continue
            for tool in conn.list_tools():
                tools.append({
                    "connector": cid,
                    "connector_name": conn.display_name,
                    "tool": tool.name,
                    "full_name": f"{cid}/{tool.name}",
                    "description": tool.description,
                    "parameters": tool.parameters,
                })
        return tools

    def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        return self._connectors.get(connector_id)

    def status_report(self) -> str:
        """Generate a human-readable status report of all connectors."""
        lines = ["### 🔌 JARVIS Connector Hub Status\n"]
        active, needs_config = [], []

        for conn in self._connectors.values():
            entry = f"{conn.icon} **{conn.display_name}** — {conn.description}"
            if conn.is_configured:
                tools_count = len(conn.list_tools())
                active.append(f"  ✅ {entry} ({tools_count} tools)")
            else:
                needs_config.append(f"  ⚙️ {entry}\n     Setup: {conn.auth_hint}")

        if active:
            lines.append("**Active Connectors:**")
            lines.extend(active)
        if needs_config:
            lines.append("\n**Needs Configuration:**")
            lines.extend(needs_config)
        if self._load_errors:
            lines.append(f"\n**Load Errors ({len(self._load_errors)}):** "
                         f"{', '.join(self._load_errors.keys())}")

        lines.append(f"\n*Total: {len(self._connectors)} connectors | "
                     f"{sum(1 for c in self._connectors.values() if c.is_configured)} active*")
        return "\n".join(lines)

    def register_with_tool_registry(self) -> int:
        """
        Register all connector tools into the JARVIS main tool registry
        so the orchestrator ReAct loop can use them.

        Returns:
            Number of tools registered.
        """
        try:
            from brjarvis.tools.registry import register_tool
        except ImportError:
            logger.warning("ConnectorHub: tool registry not available")
            return 0

        registered = 0
        for cid, conn in self._connectors.items():
            if not conn.is_configured:
                continue
            for tool in conn.list_tools():
                full_tool_name = f"connector_{cid}_{tool.name}".replace("-", "_")
                connector_ref = conn
                tool_name_ref = tool.name

                def make_action(c_ref, t_name):
                    def action(args: Dict[str, Any]) -> str:
                        return c_ref.call_tool(t_name, args)
                    action.__name__ = f"connector_{c_ref.connector_id}_{t_name}"
                    return action

                try:
                    register_tool(
                        name=full_tool_name,
                        description=f"[{conn.display_name}] {tool.description}",
                        parameters=tool.parameters,
                    )(make_action(connector_ref, tool_name_ref))
                    registered += 1
                except Exception as e:
                    logger.debug("ConnectorHub: Skipping tool %s: %s", full_tool_name, e)

        logger.info("ConnectorHub: Registered %d connector tools in JARVIS registry", registered)
        return registered


# ── Module-Level Singleton ────────────────────────────────────────────────────

_hub_singleton: Optional[ConnectorHub] = None


def get_hub() -> ConnectorHub:
    """Return the global ConnectorHub singleton (lazy-initialized)."""
    global _hub_singleton
    if _hub_singleton is None:
        _hub_singleton = ConnectorHub()
    return _hub_singleton
