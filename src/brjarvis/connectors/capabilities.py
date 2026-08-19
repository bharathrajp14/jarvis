# connectors/capabilities.py — Universal Application Capability Registry for BR JARVIS MK37
"""
Universal Application Capability Registry for BR JARVIS MK37.
Unifies all communication, productivity, engineering, research, business, local,
and mobile devices behind standard capability models.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.Capabilities")


class CapabilityCategory(str, Enum):
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    ENGINEERING = "engineering"
    RESEARCH = "research"
    BUSINESS = "business"
    LOCAL = "local"
    MCP = "mcp"
    MOBILE = "mobile"


class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ApplicationCapability:
    name: str
    display_name: str
    category: CapabilityCategory
    authenticated: bool = True
    actions: List[str] = field(default_factory=list)
    sensitivity: SensitivityLevel = SensitivityLevel.LOW
    requires_approval: bool = False
    provider_type: str = "connector"  # "connector", "desktop", "browser", "mobile"
    icon: str = "🔌"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["sensitivity"] = self.sensitivity.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApplicationCapability:
        raw = dict(data)
        if "category" in raw and isinstance(raw["category"], str):
            raw["category"] = CapabilityCategory(raw["category"])
        if "sensitivity" in raw and isinstance(raw["sensitivity"], str):
            raw["sensitivity"] = SensitivityLevel(raw["sensitivity"])
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


class CapabilityRegistry:
    """Central registry of all authenticated application and device capabilities."""

    def __init__(self):
        self._capabilities: Dict[str, ApplicationCapability] = {}
        self._register_default_capabilities()

    def register(self, cap: ApplicationCapability) -> None:
        self._capabilities[cap.name.lower().strip()] = cap
        logger.info("Capability registered: %s [%s]", cap.display_name, cap.category.value)

    def get_capability(self, name: str) -> Optional[ApplicationCapability]:
        return self._capabilities.get(name.lower().strip())

    def list_capabilities(
        self, category: Optional[CapabilityCategory] = None, authenticated_only: bool = False
    ) -> List[ApplicationCapability]:
        caps = list(self._capabilities.values())
        if category:
            caps = [c for c in caps if c.category == category]
        if authenticated_only:
            caps = [c for c in caps if c.authenticated]
        return sorted(caps, key=lambda c: c.name)

    def find_capability_for_action(self, action_name: str) -> List[ApplicationCapability]:
        act = action_name.lower().strip()
        matches = []
        for cap in self._capabilities.values():
            if any(act in a.lower() for a in cap.actions):
                matches.append(cap)
        return matches

    def _register_default_capabilities(self) -> None:
        # Communication
        self.register(
            ApplicationCapability(
                name="gmail",
                display_name="Gmail / Google Workspace",
                category=CapabilityCategory.COMMUNICATION,
                actions=["read_email", "search_email", "draft_email", "send_email"],
                sensitivity=SensitivityLevel.HIGH,
                requires_approval=True,
                icon="✉️",
                description="Manage inbox, search emails, compose drafts and send messages.",
            )
        )
        self.register(
            ApplicationCapability(
                name="whatsapp",
                display_name="WhatsApp Automation",
                category=CapabilityCategory.COMMUNICATION,
                actions=["send_message", "search_contact", "send_document", "read_recent"],
                sensitivity=SensitivityLevel.HIGH,
                requires_approval=True,
                icon="💬",
                description="Send direct WhatsApp messages and media files to contacts.",
            )
        )
        self.register(
            ApplicationCapability(
                name="slack",
                display_name="Slack Workspace",
                category=CapabilityCategory.COMMUNICATION,
                actions=["send_message", "list_channels", "search_messages"],
                sensitivity=SensitivityLevel.MEDIUM,
                requires_approval=True,
                icon="👥",
                description="Collaborate in Slack channels and direct messages.",
            )
        )

        # Productivity
        self.register(
            ApplicationCapability(
                name="google_calendar",
                display_name="Google Calendar",
                category=CapabilityCategory.PRODUCTIVITY,
                actions=["list_events", "create_event", "delete_event", "check_conflicts"],
                sensitivity=SensitivityLevel.MEDIUM,
                icon="📅",
                description="Manage schedule, calendar agenda and meeting invites.",
            )
        )
        self.register(
            ApplicationCapability(
                name="notion",
                display_name="Notion Workspace",
                category=CapabilityCategory.PRODUCTIVITY,
                actions=["search_pages", "create_page", "append_block", "query_database"],
                sensitivity=SensitivityLevel.MEDIUM,
                icon="📝",
                description="Search notes, databases, and author pages.",
            )
        )

        # Engineering
        self.register(
            ApplicationCapability(
                name="github",
                display_name="GitHub Developer",
                category=CapabilityCategory.ENGINEERING,
                actions=["list_repos", "list_prs", "create_issue", "get_commit_history"],
                sensitivity=SensitivityLevel.MEDIUM,
                icon="🐙",
                description="Inspect pull requests, repositories, and issue trackers.",
            )
        )

        # Research
        self.register(
            ApplicationCapability(
                name="browser",
                display_name="Strawberry Browser Engine",
                category=CapabilityCategory.RESEARCH,
                actions=["navigate", "search", "extract", "click", "type", "fill_form"],
                sensitivity=SensitivityLevel.LOW,
                icon="🌐",
                description="Autonomous web research, extraction and DOM interaction.",
            )
        )
        self.register(
            ApplicationCapability(
                name="youtube",
                display_name="YouTube Intelligence",
                category=CapabilityCategory.RESEARCH,
                actions=["search_videos", "get_transcript", "get_metadata"],
                sensitivity=SensitivityLevel.LOW,
                icon="🎥",
                description="Fetch video metadata and transcripts for research.",
            )
        )

        # Local Desktop
        self.register(
            ApplicationCapability(
                name="desktop_pc",
                display_name="Windows / Desktop OS Controller",
                category=CapabilityCategory.LOCAL,
                actions=["launch_app", "close_app", "window_focus", "keyboard_type", "mouse_click", "file_ops"],
                sensitivity=SensitivityLevel.MEDIUM,
                icon="💻",
                description="Control desktop applications, filesystem, and system controls.",
            )
        )


_capability_registry_instance: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    global _capability_registry_instance
    if _capability_registry_instance is None:
        _capability_registry_instance = CapabilityRegistry()
    return _capability_registry_instance
