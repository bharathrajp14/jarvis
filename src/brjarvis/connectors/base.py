# connectors/base.py — BR JARVIS BaseConnector Abstract Interface
"""
Every JARVIS connector plugin implements this interface.
Provides a unified API: authenticate, list_tools, call_tool, health_check.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.Connectors")


class ConnectorTool:
    """Describes a single callable capability of a connector."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        requires_auth: bool = False,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.requires_auth = requires_auth

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requires_auth": self.requires_auth,
        }


class BaseConnector(ABC):
    """
    Abstract base class for all JARVIS connector plugins.

    Subclasses must implement:
      - connector_id    (str property)
      - display_name    (str property)
      - description     (str property)
      - list_tools()    → list of ConnectorTool
      - call_tool()     → result string/dict
      - health_check()  → bool
    """

    @property
    @abstractmethod
    def connector_id(self) -> str:
        """Unique snake_case identifier (e.g. 'google_drive', 'github')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name (e.g. 'Google Drive', 'GitHub')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description of what this connector provides."""
        ...

    @property
    def requires_auth(self) -> bool:
        """Override to True for connectors requiring API keys / OAuth."""
        return False

    @property
    def auth_hint(self) -> str:
        """Instructions for obtaining required credentials."""
        return ""

    @property
    def is_configured(self) -> bool:
        """Return True if required credentials are present and valid."""
        return True

    @property
    def icon(self) -> str:
        """Emoji icon for display in the UI."""
        return "🔌"

    @abstractmethod
    def list_tools(self) -> List[ConnectorTool]:
        """Return the list of callable tools this connector provides."""
        ...

    @abstractmethod
    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a named tool with the given arguments.

        Returns:
            A string, dict, or list result. Strings are returned directly
            to the user. Dicts/lists are JSON-formatted.
        """
        ...

    def health_check(self) -> bool:
        """
        Verify the connector is reachable and credentials are valid.
        Returns True if healthy. Override for custom health checks.
        """
        try:
            tools = self.list_tools()
            return len(tools) > 0
        except Exception:
            return False

    def get_tool(self, name: str) -> Optional[ConnectorTool]:
        """Look up a tool by name."""
        for t in self.list_tools():
            if t.name == name:
                return t
        return None

    def __repr__(self) -> str:
        status = "✅" if self.is_configured else "⚠️ (needs config)"
        return f"<Connector {self.display_name} {status}>"
