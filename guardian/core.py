# guardian/core.py — Master Guardian Core Safety Engine
from __future__ import annotations

import logging
import hashlib
import time
from pathlib import Path
from guardian.kill_switch import KillSwitch
from guardian.snapshot import SnapshotManager
from guardian.rollback import RollbackEngine
from guardian.audit_log import AuditLog

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

PROTECTED_CORE_PATHS = [
    "guardian/core.py",
    "guardian/kill_switch.py",
    "guardian/snapshot.py",
    "guardian/rollback.py",
    "guardian/audit_log.py",
    "permissions.py",
]


class GuardianCore:
    """Master Immutable Safety Core."""

    _HASH_FILE = BASE_DIR / ".guardian_hashes.json"

    def __init__(self, integrity_interval: int = 300):
        self.integrity_interval = integrity_interval
        self._initial_hashes = self._load_or_compute_hashes()
        self._last_check = time.time()

    def _load_or_compute_hashes(self) -> dict[str, str]:
        """Load hashes from disk if available, otherwise compute and persist."""
        import json
        if self._HASH_FILE.exists():
            try:
                return json.loads(self._HASH_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.exception('Boot critical exception encountered in guardian/core.py')
                raise e
        hashes = self._calculate_hashes()
        self._persist_hashes(hashes)
        return hashes

    def _persist_hashes(self, hashes: dict[str, str]) -> None:
        """Write hashes to disk for persistence across restarts."""
        import json
        try:
            self._HASH_FILE.write_text(
                json.dumps(hashes, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.exception('Boot critical exception encountered in guardian/core.py')
            raise e
    def _calculate_hashes(self) -> dict[str, str]:
        hashes = {}
        for path_str in PROTECTED_CORE_PATHS:
            p = BASE_DIR / path_str
            if p.exists():
                try:
                    data = p.read_bytes()
                    hashes[path_str] = hashlib.sha256(data).hexdigest()
                except Exception as e:
                    logger.exception('Boot critical exception encountered in guardian/core.py')
                    raise e
        return hashes

    def rehash_integrity(self) -> None:
        """Update baseline hashes after a verified, authorized system upgrade."""
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

    def verify_integrity(self) -> dict:
        """Verify core safety files have not been modified outside release process."""
        current_hashes = self._calculate_hashes()
        mismatches = []
        for path_str, original_hash in self._initial_hashes.items():
            current_hash = current_hashes.get(path_str)
            if current_hash != original_hash:
                mismatches.append(path_str)

        self._last_check = time.time()

        if mismatches:
            # Trigger pause & audit log
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


_global_guardian_core = None


def get_guardian_core() -> GuardianCore:
    global _global_guardian_core
    if _global_guardian_core is None:
        _global_guardian_core = GuardianCore()
    return _global_guardian_core
