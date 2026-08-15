# agent/artifacts.py — Antigravity-Style Markdown Artifact Generator & Artifact Manager
"""
Artifact Document Generator and Host Artifact Lifecycle Manager for BR JARVIS.
Features:
- Renders GitHub-Flavored Markdown documents with alerts, diagrams, links, and diffs.
- Secure Sandbox-to-Host Artifact Export Pipeline.
- Complete lifecycle metadata tracking (created, exported, opened, observed, verified).
- Path traversal prevention, symlink/reparse-point escape defense, and file integrity hashing (SHA-256).
- Platform-safe configurable host artifact root (%USERPROFILE%\\Documents\\BR-JARVIS\\artifacts\\).
"""
from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import re
import shutil
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("JARVIS.Artifacts")

# Explicit allowlist of safe user-facing artifact extensions
ALLOWED_ARTIFACT_EXTENSIONS: frozenset[str] = frozenset({
    ".html", ".htm", ".md", ".markdown", ".txt", ".json", ".csv", ".tsv",
    ".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".log", ".xml", ".yaml", ".yml"
})

# Forbidden file patterns that must NEVER leave sandbox or be exported
BLOCKED_ARTIFACT_NAMES: frozenset[str] = frozenset({
    ".env", ".env.local", ".env.production", ".git", ".gitignore", ".npmrc",
    ".pypirc", "id_rsa", "id_ed25519", "id_dsa", "known_hosts", "authorized_keys",
    "credentials", "secrets.json", "secrets.yaml", "secrets.env", "passwd",
    "shadow", "sam", "system32"
})

BLOCKED_ARTIFACT_EXTENSIONS: frozenset[str] = frozenset({
    ".exe", ".dll", ".so", ".dylib", ".sh", ".bat", ".ps1", ".cmd", ".vbs",
    ".pem", ".key", ".pfx", ".pkcs12", ".env", ".pyc", ".pyo"
})


@dataclass
class ArtifactMetadata:
    summary: str
    user_facing: bool = True
    request_feedback: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class ArtifactRecord:
    """Represents a tracked user-facing artifact through its complete lifecycle."""
    artifact_id: str
    task_id: str = "default"
    sandbox_path: Optional[str] = None
    host_path: Optional[str] = None
    filename: str = ""
    mime_type: str = "application/octet-stream"
    size: int = 0
    sha256: str = ""
    created_at: float = field(default_factory=time.time)
    created: bool = True
    exported: bool = False
    opened: bool = False
    observed: bool = False
    host_verified: bool = False
    browser_verified: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArtifactManager:
    """
    Authoritative Manager for user-facing artifacts.
    Enforces security boundary checks, safe host export, and verification.
    """

    def __init__(self, host_artifacts_dir: Optional[Union[str, Path]] = None):
        self._lock = threading.Lock()
        self._records: Dict[str, ArtifactRecord] = {}

        if host_artifacts_dir:
            self._host_artifacts_dir = Path(host_artifacts_dir).resolve()
        else:
            env_dir = os.environ.get("JARVIS_ARTIFACTS_DIR")
            if env_dir:
                self._host_artifacts_dir = Path(env_dir).resolve()
            else:
                self._host_artifacts_dir = (Path.home() / "Documents" / "BR-JARVIS" / "artifacts").resolve()

        try:
            self._host_artifacts_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("Could not create default host artifacts directory: %s", e)

    @property
    def host_artifacts_dir(self) -> Path:
        return self._host_artifacts_dir

    def get_host_artifact_dir(self) -> Path:
        self._host_artifacts_dir.mkdir(parents=True, exist_ok=True)
        return self._host_artifacts_dir

    @staticmethod
    def compute_sha256(filepath: Union[str, Path]) -> str:
        """Compute SHA-256 hex digest of a file."""
        p = Path(filepath)
        if not p.is_file():
            return ""
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def get_mime_type(filename: str) -> str:
        """Guess MIME type from filename."""
        mime, _ = mimetypes.guess_type(filename)
        return mime or "application/octet-stream"

    @classmethod
    def is_allowed_artifact(cls, path_or_name: Union[str, Path]) -> Tuple[bool, str]:
        """Validate if a file is permitted to be exported from sandbox."""
        p = Path(path_or_name)
        name_lower = p.name.lower()
        suffix_lower = p.suffix.lower()

        # Check blocked names
        if name_lower in BLOCKED_ARTIFACT_NAMES or name_lower.startswith(".env"):
            return False, f"File name '{p.name}' matches critical secret/system denylist."

        for blocked_part in BLOCKED_ARTIFACT_NAMES:
            if blocked_part in name_lower:
                return False, f"File name '{p.name}' contains blocked identifier '{blocked_part}'."

        # Check blocked extensions
        if suffix_lower in BLOCKED_ARTIFACT_EXTENSIONS:
            return False, f"Extension '{suffix_lower}' is blocked for security."

        # Check allowed extensions
        if suffix_lower not in ALLOWED_ARTIFACT_EXTENSIONS:
            return False, f"Extension '{suffix_lower}' is not in approved artifact allowlist."

        return True, "OK"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal or invalid characters."""
        # Strip path separators
        clean = os.path.basename(str(filename).strip().replace("\\", "/"))
        # Remove dangerous characters
        clean = re.sub(r'[^\w\-_\.]', '_', clean)
        if not clean or clean in (".", ".."):
            clean = f"artifact_{uuid.uuid4().hex[:8]}.txt"
        return clean

    def _get_unique_destination(self, base_name: str, allow_overwrite: bool = False) -> Path:
        """Resolve a unique non-colliding destination path inside the host artifact root."""
        host_root = self.get_host_artifact_dir()
        dest = host_root / base_name

        if allow_overwrite or not dest.exists():
            return dest

        # Generate unique collision-free filename
        stem = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = host_root / f"{stem}_{counter}{suffix}"
            counter += 1
        return dest

    def export_sandbox_artifact(
        self,
        sandbox_path: Union[str, Path],
        task_id: str = "default",
        custom_filename: Optional[str] = None,
        allow_overwrite: bool = False,
    ) -> ArtifactRecord:
        """
        Securely exports an artifact generated in sandbox jail to the verified host directory.
        Steps:
        1. Verify source exists inside sandbox.
        2. Validate artifact is permitted to leave sandbox.
        3. Create/verify host artifact directory.
        4. Canonicalize destination and prevent path traversal / symlink escapes.
        5. Copy artifact safely (atomic write).
        6. Verify destination exists and is readable.
        7. Calculate destination hash and compare with source hash.
        8. Record verified artifact.
        """
        artifact_id = f"art_{uuid.uuid4().hex[:12]}"
        src_path = Path(sandbox_path)

        # 1. Verify source exists
        if not src_path.exists():
            err_msg = f"Source artifact not found at: {sandbox_path}"
            logger.error("Export failed: %s", err_msg)
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(sandbox_path),
                filename=src_path.name,
                created=False,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        if not src_path.is_file():
            err_msg = f"Source path is not a regular file: {sandbox_path}"
            logger.error("Export failed: %s", err_msg)
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(sandbox_path),
                filename=src_path.name,
                created=True,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        # Check symlink escapes
        try:
            resolved_src = src_path.resolve(strict=True)
        except Exception as e:
            err_msg = f"Cannot resolve source path: {e}"
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(sandbox_path),
                filename=src_path.name,
                created=True,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        # 2. Validate artifact security policy
        filename = self._sanitize_filename(custom_filename or src_path.name)
        allowed, reason = self.is_allowed_artifact(filename)
        if not allowed:
            err_msg = f"Security export violation: {reason}"
            logger.warning("Export blocked: %s", err_msg)
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(resolved_src),
                filename=filename,
                created=True,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        # 3. Source hash and size
        src_hash = self.compute_sha256(resolved_src)
        try:
            src_size = resolved_src.stat().st_size
        except Exception:
            src_size = 0

        # 4. Resolve and canonicalize destination
        host_root = self.get_host_artifact_dir()
        dest_path = self._get_unique_destination(filename, allow_overwrite=allow_overwrite)

        # Boundary check: Ensure destination does not escape host_root
        try:
            dest_canonical = dest_path.resolve(strict=False)
            dest_canonical.relative_to(host_root)
        except ValueError:
            err_msg = f"Path traversal detected: Destination '{dest_path}' escapes host directory '{host_root}'."
            logger.error("Security violation: %s", err_msg)
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(resolved_src),
                filename=filename,
                size=src_size,
                sha256=src_hash,
                created=True,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        # 5. Copy file safely
        try:
            temp_dest = dest_canonical.parent / f".tmp_{uuid.uuid4().hex[:8]}_{dest_canonical.name}"
            shutil.copy2(resolved_src, temp_dest)
            # Atomic replace
            os.replace(temp_dest, dest_canonical)
        except Exception as e:
            err_msg = f"Failed to copy artifact to host destination '{dest_canonical}': {e}"
            logger.error("Copy error: %s", err_msg)
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(resolved_src),
                host_path=str(dest_canonical),
                filename=dest_canonical.name,
                size=src_size,
                sha256=src_hash,
                created=True,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        # 6. Verify destination exists and is readable
        if not dest_canonical.exists() or not dest_canonical.is_file():
            err_msg = f"Destination verification failed: '{dest_canonical}' does not exist."
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(resolved_src),
                host_path=str(dest_canonical),
                filename=dest_canonical.name,
                size=src_size,
                sha256=src_hash,
                created=True,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        if not os.access(dest_canonical, os.R_OK):
            err_msg = f"Destination is not readable: '{dest_canonical}'"
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(resolved_src),
                host_path=str(dest_canonical),
                filename=dest_canonical.name,
                size=src_size,
                sha256=src_hash,
                created=True,
                exported=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        # 7. Destination hash verification
        dest_hash = self.compute_sha256(dest_canonical)
        if dest_hash != src_hash:
            err_msg = f"Integrity error: Destination hash '{dest_hash}' does not match source hash '{src_hash}'."
            logger.error("Hash mismatch: %s", err_msg)
            rec = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                sandbox_path=str(resolved_src),
                host_path=str(dest_canonical),
                filename=dest_canonical.name,
                size=src_size,
                sha256=src_hash,
                created=True,
                exported=False,
                host_verified=False,
                error=err_msg
            )
            with self._lock:
                self._records[artifact_id] = rec
            return rec

        # Success: Record verified artifact
        rec = ArtifactRecord(
            artifact_id=artifact_id,
            task_id=task_id,
            sandbox_path=str(resolved_src),
            host_path=str(dest_canonical),
            filename=dest_canonical.name,
            mime_type=self.get_mime_type(dest_canonical.name),
            size=dest_canonical.stat().st_size,
            sha256=dest_hash,
            created_at=time.time(),
            created=True,
            exported=True,
            host_verified=True,
            error=None
        )

        with self._lock:
            self._records[artifact_id] = rec
            # Also map by host_path for fast lookup
            self._records[str(dest_canonical)] = rec

        logger.info("⚡ Successfully exported artifact '%s' -> '%s' (SHA256: %s)", filename, dest_canonical, dest_hash[:12])
        return rec

    def ensure_host_artifact(
        self,
        path_or_url: Union[str, Path],
        task_id: str = "default",
        allow_export: bool = True,
    ) -> Tuple[bool, str, Optional[ArtifactRecord]]:
        """
        Intercepts any file path or URL before handing off to browser tools:
        - If already a web URL (http://, https://), passes through unchanged.
        - If a sandbox jail path, automatically exports it safely to the host artifact directory.
        - If a regular host file, verifies it exists and is readable.
        Returns: (success: bool, verified_host_path_or_url: str, record: Optional[ArtifactRecord])
        """
        target = str(path_or_url).strip()
        if not target:
            return False, "Target path or URL is empty.", None

        # Pass web URLs through
        if target.startswith(("http://", "https://", "about:", "chrome:", "edge:")):
            return True, target, None

        # Clean file:// prefix if passed
        if target.startswith("file:///"):
            clean_path = target[8:] if sys.platform == "win32" else target[7:]
        elif target.startswith("file://"):
            clean_path = target[7:]
        else:
            clean_path = target

        p = Path(clean_path)

        # Detect sandbox jail path
        norm_str = str(clean_path).replace("\\", "/").lower()
        is_sandbox = "jarvis_sandbox_jails" in norm_str or "sandbox_jails" in norm_str or "jail_" in norm_str

        if is_sandbox:
            if not allow_export:
                return False, "Raw sandbox paths cannot be accessed directly by browser tools.", None

            # Attempt export
            if p.exists():
                rec = self.export_sandbox_artifact(p, task_id=task_id)
                if rec.exported and rec.host_path:
                    return True, rec.host_path, rec
                else:
                    return False, f"Artifact created, but could not export it to the user workspace: {rec.error}", rec
            else:
                # Check if it was already exported and we have a record
                with self._lock:
                    for r in self._records.values():
                        if r.sandbox_path and Path(r.sandbox_path).name == p.name and r.exported and r.host_path:
                            if Path(r.host_path).exists():
                                return True, r.host_path, r
                return False, f"Artifact created, but could not export it to the user workspace: Sandbox file '{p.name}' is missing.", None

        # Regular host path
        try:
            resolved = p.resolve()
            if not resolved.exists():
                return False, f"File not found on host: {target}", None
            if not resolved.is_file():
                return False, f"Path is not a file: {target}", None
            if not os.access(resolved, os.R_OK):
                return False, f"File is not readable: {target}", None

            with self._lock:
                rec = self._records.get(str(resolved))

            return True, str(resolved), rec
        except Exception as e:
            return False, f"Error validating host path '{target}': {e}", None

    def record_browser_result(
        self,
        artifact_id_or_path: str,
        opened: bool = False,
        observed: bool = False,
        browser_verified: bool = False,
        error: Optional[str] = None
    ) -> Optional[ArtifactRecord]:
        """Update browser verification lifecycle state on an artifact record."""
        with self._lock:
            rec = self._records.get(artifact_id_or_path)
            if not rec:
                for r in self._records.values():
                    if r.host_path == artifact_id_or_path or r.sandbox_path == artifact_id_or_path or r.filename == artifact_id_or_path:
                        rec = r
                        break
            if rec:
                rec.opened = opened
                rec.observed = observed
                rec.browser_verified = browser_verified
                if error:
                    rec.error = error
                return rec
        return None

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        with self._lock:
            return self._records.get(artifact_id)

    def list_artifacts(self) -> List[ArtifactRecord]:
        with self._lock:
            # Return unique records by artifact_id
            seen = set()
            res = []
            for r in self._records.values():
                if r.artifact_id not in seen:
                    seen.add(r.artifact_id)
                    res.append(r)
            return res

    def clear(self) -> None:
        """Clear artifact registry for testing."""
        with self._lock:
            self._records.clear()


_GLOBAL_ARTIFACT_MANAGER: Optional[ArtifactManager] = None
_GLOBAL_MGR_LOCK = threading.Lock()


def get_artifact_manager() -> ArtifactManager:
    global _GLOBAL_ARTIFACT_MANAGER
    with _GLOBAL_MGR_LOCK:
        if _GLOBAL_ARTIFACT_MANAGER is None:
            _GLOBAL_ARTIFACT_MANAGER = ArtifactManager()
        return _GLOBAL_ARTIFACT_MANAGER


# ─────────────────────────────────────────────────────────────────────────────
# Markdown Artifact Document Generator (Antigravity Specification)
# ─────────────────────────────────────────────────────────────────────────────

class ArtifactDocument:
    """Represents a structured Markdown artifact document."""

    def __init__(self, title: str, filepath: str | Path, metadata: Optional[ArtifactMetadata] = None):
        self.title = title
        self.filepath = Path(filepath)
        self.metadata = metadata or ArtifactMetadata(summary=title)
        self.sections: List[Dict[str, str]] = []
        self._content_chunks: List[str] = []

    def add_alert(self, alert_type: str, text: str) -> ArtifactDocument:
        """Add a GitHub-style alert callout: NOTE, TIP, IMPORTANT, WARNING, CAUTION."""
        atype = alert_type.upper()
        if atype not in ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"):
            atype = "NOTE"
        self._content_chunks.append(f"> [!{atype}]\n> {text.replace(chr(10), chr(10) + '> ')}")
        return self

    def add_section(self, heading: str, body: str, level: int = 2) -> ArtifactDocument:
        prefix = "#" * max(1, min(6, level))
        self._content_chunks.append(f"{prefix} {heading}\n\n{body.strip()}")
        return self

    def add_mermaid_diagram(self, mermaid_code: str) -> ArtifactDocument:
        self._content_chunks.append(f"```mermaid\n{mermaid_code.strip()}\n```")
        return self

    def add_code_diff(self, old_code: str, new_code: str, filename: str = "") -> ArtifactDocument:
        diff_lines = []
        if filename:
            diff_lines.append(f"--- a/{filename}")
            diff_lines.append(f"+++ b/{filename}")
        for l in old_code.splitlines():
            diff_lines.append(f"-{l}")
        for l in new_code.splitlines():
            diff_lines.append(f"+{l}")
        self._content_chunks.append("```diff\n" + "\n".join(diff_lines) + "\n```")
        return self

    def render(self) -> str:
        header = f"# {self.title}\n\n"
        body = "\n\n".join(self._content_chunks)
        return header + body

    def save(self) -> Path:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.render()
        self.filepath.write_text(content, encoding="utf-8")
        return self.filepath.resolve()


def make_file_link(filepath: str | Path, text: str | None = None, start_line: int | None = None, end_line: int | None = None) -> str:
    """Format clickable file:// markdown link."""
    p = Path(filepath).resolve()
    uri = p.as_uri()
    if start_line is not None:
        if end_line is not None and end_line != start_line:
            uri += f"#L{start_line}-L{end_line}"
        else:
            uri += f"#L{start_line}"
    label = text or p.name
    return f"[{label}]({uri})"
