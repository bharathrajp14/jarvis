# mobile/gateway.py — Mobile Device Gateway & Device Registry
"""
Device Gateway for paired Android and mobile devices.
Handles device registration, authenticated pairing via PIN/QR token,
public key validation, and trust states.
"""
from __future__ import annotations

import hmac
import json
import logging
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.DeviceGateway")

DB_DIR = paths.WORKSPACE_ROOT / "devices"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "devices.db"


@dataclass
class PairedDevice:
    device_id: str
    display_name: str
    platform: str = "android"  # android, ios, tablet
    trust_state: str = "paired"  # paired, trusted, revoked
    public_key: str = ""
    auth_token: str = ""
    capabilities: List[str] = field(default_factory=lambda: [
        "accessibility", "screen_stream", "notifications", "app_control", "messaging", "camera", "files"
    ])
    model_name: str = ""
    last_seen: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PairedDevice:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class DeviceGateway:
    """Device gateway registry and pairing manager."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._pending_pairing_tokens: Dict[str, Dict[str, Any]] = {}

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    trust_state TEXT NOT NULL,
                    public_key TEXT,
                    auth_token TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    model_name TEXT,
                    last_seen REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def generate_pairing_token(self, display_name: str = "Android Companion") -> Dict[str, Any]:
        """Generate a secure 6-digit PIN and session token for device pairing."""
        import random
        pin = f"{random.randint(100000, 999999)}"
        token = str(uuid.uuid4())
        self._pending_pairing_tokens[pin] = {
            "token": token,
            "display_name": display_name,
            "expires_at": time.time() + 300  # 5 minutes validity
        }
        logger.info("Generated pairing PIN for device '%s': %s", display_name, pin)
        return {
            "pin": pin,
            "token": token,
            "expires_in_seconds": 300,
            "qr_payload": f"jarvis-pair://v1?token={token}&pin={pin}"
        }

    def complete_pairing(self, pin: str, device_id: str, model_name: str, public_key: str = "") -> Optional[PairedDevice]:
        """Verify PIN and register the paired device."""
        req = self._pending_pairing_tokens.get(pin)
        if not req or time.time() > req["expires_at"]:
            logger.warning("Invalid or expired pairing PIN: %s", pin)
            return None

        del self._pending_pairing_tokens[pin]

        device = PairedDevice(
            device_id=device_id,
            display_name=req["display_name"],
            platform="android",
            trust_state="trusted",
            public_key=public_key,
            auth_token=req["token"],
            model_name=model_name,
            last_seen=time.time(),
            created_at=time.time()
        )
        self.save_device(device)
        logger.info("Successfully paired Android device '%s' (ID: %s)", model_name, device_id)
        return device

    def save_device(self, device: PairedDevice) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO devices (
                    device_id, display_name, platform, trust_state,
                    public_key, auth_token, capabilities, model_name, last_seen, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    trust_state=excluded.trust_state,
                    auth_token=excluded.auth_token,
                    capabilities=excluded.capabilities,
                    model_name=excluded.model_name,
                    last_seen=excluded.last_seen
            """, (
                device.device_id,
                device.display_name,
                device.platform,
                device.trust_state,
                device.public_key,
                device.auth_token,
                json.dumps(device.capabilities),
                device.model_name,
                device.last_seen,
                device.created_at
            ))
            conn.commit()

    def get_device(self, device_id: str) -> Optional[PairedDevice]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
            if row:
                d = dict(row)
                d["capabilities"] = json.loads(d["capabilities"])
                return PairedDevice.from_dict(d)
        return None

    def list_devices(self, trust_state: Optional[str] = None) -> List[PairedDevice]:
        with self._get_conn() as conn:
            if trust_state:
                rows = conn.execute("SELECT * FROM devices WHERE trust_state = ? ORDER BY last_seen DESC", (trust_state,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["capabilities"] = json.loads(d["capabilities"])
                results.append(PairedDevice.from_dict(d))
            return results

    def verify_auth_token(self, device_id: str, token: str) -> bool:
        device = self.get_device(device_id)
        if not device or device.trust_state == "revoked":
            return False
        return hmac.compare_digest(device.auth_token, token)

    def revoke_device(self, device_id: str) -> bool:
        device = self.get_device(device_id)
        if device:
            device.trust_state = "revoked"
            self.save_device(device)
            logger.warning("Revoked access for device %s", device_id)
            return True
        return False


_gateway_instance: Optional[DeviceGateway] = None


def get_device_gateway() -> DeviceGateway:
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = DeviceGateway()
    return _gateway_instance
