# career/notifications.py — Priority & Actionable Notification Engine
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from career.models import PriorityLevel
from events.bus import get_event_bus
from events.types import BaseEvent

logger = logging.getLogger("JARVIS.CareerNotifications")


@dataclass
class CareerNotification:
    notification_id: str = field(default_factory=lambda: f"NOTIF-{uuid.uuid4().hex[:8].upper()}")
    event_type: str = "CAREER_UPDATE"
    title: str = ""
    message: str = ""
    priority: PriorityLevel = PriorityLevel.MEDIUM
    application_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    read: bool = False
    action_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["priority"] = self.priority.value if isinstance(self.priority, PriorityLevel) else str(self.priority)
        return d


class CareerNotificationEngine:
    """
    Evaluates career event priority (CRITICAL, HIGH, MEDIUM, LOW)
    and broadcasts high-value actionable alerts.
    """

    _INSTANCE: Optional[CareerNotificationEngine] = None

    def __init__(self):
        self.notifications: List[CareerNotification] = []
        self.event_bus = get_event_bus()

    @classmethod
    def get_instance(cls) -> CareerNotificationEngine:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def notify_career_event(
        self,
        event_type: str,
        title: str,
        message: str,
        priority: PriorityLevel = PriorityLevel.MEDIUM,
        application_id: Optional[str] = None,
        action_url: Optional[str] = None,
    ) -> CareerNotification:
        """Create and broadcast an actionable career notification."""
        notif = CareerNotification(
            notification_id=f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            event_type=event_type,
            title=title,
            message=message,
            priority=priority,
            application_id=application_id,
            action_url=action_url,
        )

        self.notifications.append(notif)
        if len(self.notifications) > 200:
            self.notifications = self.notifications[-200:]

        log_level = logging.INFO
        if priority == PriorityLevel.CRITICAL:
            log_level = logging.CRITICAL
            logger.critical("🚨 [CRITICAL ALERT] %s: %s", title, message)
        elif priority == PriorityLevel.HIGH:
            log_level = logging.WARNING
            logger.warning("⚡ [HIGH PRIORITY] %s: %s", title, message)
        else:
            logger.info("ℹ️ [%s] %s: %s", priority.value, title, message)

        return notif

    def list_notifications(self, unread_only: bool = False, limit: int = 50) -> List[CareerNotification]:
        """List notifications in reverse chronological order."""
        if unread_only:
            items = [n for n in self.notifications if not n.read]
        else:
            items = self.notifications
        return sorted(items, key=lambda n: n.created_at, reverse=True)[:limit]

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for n in self.notifications:
            if n.notification_id == notification_id:
                n.read = True
                return True
        return False


def get_career_notification_engine() -> CareerNotificationEngine:
    return CareerNotificationEngine.get_instance()
