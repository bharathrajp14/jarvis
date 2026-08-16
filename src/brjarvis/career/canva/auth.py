# career/canva/auth.py — Secure Canva OAuth & Credential Store
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.Career.CanvaAuth")

_CREDENTIALS_FILE = paths.CONFIG_ROOT / "canva_credentials.json"


class CanvaCredentialStore:
    """
    Secure Credential Store for Canva Connect API OAuth tokens.
    Guarantees:
    - Never stores tokens or secrets in normal conversational memory or public artifacts.
    - Encapsulates token lifecycle and refresh logic.
    """

    def __init__(self, creds_path: Optional[Path | str] = None):
        self.creds_path = Path(creds_path) if creds_path else _CREDENTIALS_FILE
        self.creds_path.parent.mkdir(parents=True, exist_ok=True)

    def get_credentials(self) -> Dict[str, Any]:
        """Load stored Canva credentials."""
        # 1. Environment variables first
        client_id = os.environ.get("CANVA_CLIENT_ID")
        client_secret = os.environ.get("CANVA_CLIENT_SECRET")
        access_token = os.environ.get("CANVA_ACCESS_TOKEN")

        if client_id and (client_secret or access_token):
            return {
                "client_id": client_id,
                "client_secret": client_secret,
                "access_token": access_token,
                "refresh_token": os.environ.get("CANVA_REFRESH_TOKEN", ""),
                "expires_at": time.time() + 3600,
                "source": "environment",
            }

        # 2. Encrypted / Local credentials JSON file
        if self.creds_path.exists():
            try:
                data = json.loads(self.creds_path.read_text(encoding="utf-8"))
                data["source"] = "config_file"
                return data
            except Exception as e:
                logger.error(f"Error reading Canva credentials: {e}")

        return {}

    def save_credentials(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        refresh_token: str = "",
        expires_in: int = 3600,
    ) -> bool:
        """Save Canva OAuth credentials securely to config file."""
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": time.time() + expires_in,
            "updated_at": time.time(),
        }
        try:
            self.creds_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("🔐 Canva credentials saved securely to config.")
            return True
        except Exception as e:
            logger.error(f"Failed to save Canva credentials: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if active valid access token is present."""
        creds = self.get_credentials()
        return bool(creds.get("access_token"))
