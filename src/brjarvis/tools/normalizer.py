# src/brjarvis/tools/normalizer.py — Deterministic Tool Argument Normalizer
"""
Deterministic Tool Argument Normalizer for BR JARVIS.
Normalizes paths, URLs, enums, booleans, and schema defaults before validation and execution.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from brjarvis.core.paths import paths
from .domain import ToolDefinition

logger = logging.getLogger("JARVIS.Tools.Normalizer")


class ArgumentNormalizer:
    """Single authoritative argument normalization stage."""

    PATH_KEYS = {
        "path", "file_path", "target_path", "dir_path", "source_path",
        "destination_path", "destination", "folder", "filename", "filepath",
        "out_path", "output_path", "sandbox_path", "host_path"
    }

    URL_KEYS = {"url", "target_url", "link", "uri", "web_url", "site_url"}

    BOOLEAN_PREFIXES = ("is_", "use_", "enable_", "has_", "should_", "auto_")
    BOOLEAN_SUFFIXES = ("_enabled", "_required", "_mode", "_flag")

    @classmethod
    def normalize_args(
        cls,
        tool_def: Optional[ToolDefinition],
        args: Dict[str, Any],
        workspace_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically normalize all parameters in `args` according to schema and tool contract.
        """
        normalized = dict(args) if isinstance(args, dict) else {}
        ws = (workspace_root or paths.WORKSPACE_ROOT).resolve()

        # 1. Apply Schema Defaults if defined and missing
        if tool_def and tool_def.parameters:
            props = tool_def.parameters.get("properties", {})
            for p_name, p_spec in props.items():
                if p_name not in normalized and "default" in p_spec:
                    normalized[p_name] = p_spec["default"]

        # 2. Iterate and Normalize Types & Representations
        for key, value in list(normalized.items()):
            if value is None:
                continue

            # String Sanitization & Stripping
            if isinstance(value, str):
                v_str = value.strip()

                # A. Boolean Normalization
                if cls._is_boolean_key(key, tool_def):
                    low_val = v_str.lower()
                    if low_val in ("true", "yes", "1", "y", "t", "on"):
                        normalized[key] = True
                        continue
                    elif low_val in ("false", "no", "0", "n", "f", "off"):
                        normalized[key] = False
                        continue

                # B. Path Normalization & Traversal Defense
                if key.lower() in cls.PATH_KEYS:
                    normalized[key] = cls._normalize_path_string(v_str, ws)
                    continue

                # C. URL Protocol Normalization
                if key.lower() in cls.URL_KEYS:
                    normalized[key] = cls._normalize_url(v_str)
                    continue

                # D. Enum Value Case Normalization
                if tool_def and tool_def.parameters:
                    props = tool_def.parameters.get("properties", {})
                    if key in props and "enum" in props[key]:
                        allowed = props[key]["enum"]
                        for opt in allowed:
                            if str(opt).lower() == v_str.lower():
                                normalized[key] = opt
                                break

        return normalized

    @classmethod
    def _is_boolean_key(cls, key: str, tool_def: Optional[ToolDefinition]) -> bool:
        """Check if a parameter is defined as boolean or follows standard boolean naming."""
        if tool_def and tool_def.parameters:
            prop = tool_def.parameters.get("properties", {}).get(key, {})
            if prop.get("type") == "boolean":
                return True

        k_low = key.lower()
        if k_low in ("force", "recursive", "headless", "overwrite", "confirmed", "verified", "auto_open"):
            return True
        if any(k_low.startswith(p) for p in cls.BOOLEAN_PREFIXES):
            return True
        if any(k_low.endswith(s) for s in cls.BOOLEAN_SUFFIXES):
            return True
        return False

    @classmethod
    def _normalize_path_string(cls, path_str: str, workspace_root: Path) -> str:
        """Normalize slashes, strip redundant workspace prefixes, and resolve safe path."""
        clean = path_str.strip().replace("\\", "/")

        # Empty path defaults to workspace root
        if not clean or clean == ".":
            return "."

        # Strip redundant leading './'
        if clean.startswith("./"):
            clean = clean[2:]

        # Avoid double-workspace nesting (e.g. 'workspace/Reports/doc.docx')
        ws_name = workspace_root.name.lower()
        if clean.lower().startswith(f"{ws_name}/"):
            clean = clean[len(ws_name) + 1:]

        # Check for path traversal attempts '../'
        if ".." in clean.split("/"):
            # Resolve against workspace and verify containment
            resolved = (workspace_root / clean).resolve()
            try:
                resolved.relative_to(workspace_root)
                # Safe relative path inside workspace
                return str(resolved.relative_to(workspace_root)).replace("\\", "/")
            except ValueError:
                # Outside workspace traversal detected — sanitize to bare name
                logger.warning(f"Path traversal detected in argument '{path_str}'. Confining to workspace.")
                return Path(clean).name

        return clean

    @classmethod
    def _normalize_url(cls, url_str: str) -> str:
        """Ensure standard protocol prefix for web URLs."""
        clean = url_str.strip()
        if not clean:
            return clean

        if clean.startswith(("http://", "https://", "file://", "ws://", "wss://", "about:", "chrome:", "edge:")):
            return clean

        # If it looks like a domain name (e.g. google.com, mail.google.com), prefix https://
        if "." in clean and not clean.startswith("/") and not clean.startswith("\\"):
            return f"https://{clean}"

        return clean
