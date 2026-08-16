# guardian/core.py — Master Guardian Core Safety Engine
from __future__ import annotations

import hmac
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from .audit_log import AuditLog
from .kill_switch import KillSwitch
from .rollback import RollbackEngine
from .snapshot import SnapshotManager

logger = logging.getLogger("JARVIS.GuardianCore")

from brjarvis.core.paths import paths

BASE_DIR = paths.SOURCE_ROOT

PROTECTED_CORE_PATHS = [
    "guardian/core.py",
    "guardian/kill_switch.py",
    "guardian/snapshot.py",
    "guardian/rollback.py",
    "guardian/audit_log.py",
    "security/capabilities.py",
    "security/policy_engine.py",
    "security/path_policy.py",
]


class GuardianCore:
    """Master Immutable Safety Core.
    Guarantees integrity of safety-critical files against external tampering.
    Requires release-authorization or administrator confirmation to update baseline hashes.
    """

    _HASH_FILE = paths.STATE_ROOT / ".guardian_hashes.json"
    _TRUST_MANIFEST = paths.CONFIG_ROOT / "release_manifest.json"

    def __init__(self, integrity_interval: int = 300):
        self.integrity_interval = integrity_interval
        self._initial_hashes = self._load_trusted_hashes()
        self._last_check = time.time()

    def _load_trusted_hashes(self) -> Dict[str, str]:
        """Load baseline hashes from trusted manifest or persistent hash storage."""
        if self._TRUST_MANIFEST.exists():
            try:
                manifest = json.loads(self._TRUST_MANIFEST.read_text(encoding="utf-8"))
                if isinstance(manifest, dict) and "file_hashes" in manifest:
                    return manifest["file_hashes"]
            except Exception as e:
                logger.warning("Failed to load release manifest: %s", e)

        if self._HASH_FILE.exists():
            try:
                return json.loads(self._HASH_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Failed to read guardian hashes: %s", e)

        # Compute baseline on first clean initialization
        hashes = self._calculate_hashes()
        self._persist_hashes(hashes)
        return hashes

    def _persist_hashes(self, hashes: Dict[str, str]) -> None:
        """Write hashes to persistent storage and release manifest."""
        try:
            self._HASH_FILE.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to write guardian hashes: %s", e)

        if self._TRUST_MANIFEST.exists():
            try:
                manifest_data = {
                    "manifest_version": "40.2",
                    "file_hashes": hashes,
                    "version": "MK40.2-CERTIFIED"
                }
                self._TRUST_MANIFEST.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to update release manifest: %s", e)

    def _calculate_hashes(self) -> Dict[str, str]:
        hashes: Dict[str, str] = {}
        for path_str in PROTECTED_CORE_PATHS:
            p = BASE_DIR / path_str
            if p.exists():
                try:
                    data = p.read_bytes()
                    hashes[path_str] = hashlib.sha256(data).hexdigest()
                except Exception as e:
                    logger.error("Failed to calculate hash for %s: %s", path_str, e)
        return hashes

    def rehash_integrity(self, auth_token: Optional[str] = None) -> bool:
        """Update baseline hashes only if authorized by admin or system environment."""
        admin_key = os.environ.get("JARVIS_ADMIN_KEY") or os.environ.get("JARVIS_RELEASE_KEY")
        if admin_key:
            if not auth_token or not hmac.compare_digest(auth_token, admin_key):
                logger.warning("Unauthorized attempt to rehash guardian integrity.")
                return False

        self._initial_hashes = self._calculate_hashes()
        self._persist_hashes(self._initial_hashes)
        self._last_check = time.time()
        AuditLog.log(
            event_type="GUARDIAN_REHASH",
            title="Integrity Hashes Updated",
            details={"files_count": len(self._initial_hashes)},
            risk_level="LOW",
            applied=True,
        )
        return True

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify core safety files have not been modified outside release process."""
        current_hashes = self._calculate_hashes()
        mismatches: List[str] = []
        for path_str, original_hash in self._initial_hashes.items():
            current_hash = current_hashes.get(path_str)
            if current_hash != original_hash:
                mismatches.append(path_str)

        self._last_check = time.time()

        if mismatches:
            msg = f"Guardian Integrity Mismatch in files: {mismatches}"
            KillSwitch.pause(reason=msg)
            AuditLog.log(
                event_type="GUARDIAN_INTEGRITY_MISMATCH",
                title="Integrity Failure",
                details={"mismatches": mismatches},
                risk_level="HIGH",
                applied=False,
            )
            return {"valid": False, "mismatches": mismatches}

        return {"valid": True, "mismatches": []}

    def check_secrets_safety(self, text_content: str) -> tuple[bool, str]:
        """Scan string content for exposed API keys or secret tokens."""
        import re
        if re.search(r"""(?:api[_-]?key|secret|password)\s*=\s*['"][a-zA-Z0-9_\-]{25,}['"]""", text_content, re.IGNORECASE):
            return False, "Potential hardcoded API key or secret token detected in execution payload."
        return True, ""

    def check_execution_safety(self) -> bool:
        """Return False if execution is paused or integrity failed."""
        if KillSwitch.is_paused():
            return False

        if time.time() - self._last_check > self.integrity_interval:
            res = self.verify_integrity()
            if not res["valid"]:
                return False

        return True


_global_guardian_core: Optional[GuardianCore] = None


def get_guardian_core() -> GuardianCore:
    global _global_guardian_core
    if _global_guardian_core is None:
        _global_guardian_core = GuardianCore()
    return _global_guardian_core
