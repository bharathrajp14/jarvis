# src/brjarvis/tools/resolver.py — Tool Resolution & Semantic Capability Routing
"""
Deterministic Tool Resolver and Capability Router for BR JARVIS.
Resolves tool identifiers, namespaces, versions, deprecations, and semantic aliases without lossy transformations.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

from .domain import ToolDefinition, ToolErrorCode

logger = logging.getLogger("JARVIS.Tools.Resolver")


class ToolResolver:
    """
    Authoritative capability resolver.
    Translates model tool requests into registered ToolDefinitions.
    """

    # Canonical Namespace Mapping (flat name <-> namespaced name)
    NAMESPACE_MAP: Dict[str, str] = {
        "file_read": "filesystem.read",
        "file_write": "filesystem.write",
        "file_list": "filesystem.list",
        "file_delete": "filesystem.delete",
        "file_search": "filesystem.search",
        "browser_open_url": "browser.open",
        "browser_click": "browser.click",
        "browser_type": "browser.type",
        "browser_extract_text": "browser.extract",
        "browser_screenshot": "browser.screenshot",
        "browser_close": "browser.close",
        "web_search": "web.search",
        "fetch_page": "web.fetch",
        "fetch_raw": "web.fetch_raw",
        "open_app": "system.open_app",
        "computer_settings": "system.settings",
        "cli_controller": "system.cli",
        "send_email": "communication.email",
        "send_whatsapp": "communication.whatsapp",
        "create_calendar_event": "calendar.create",
        "list_calendar_events": "calendar.list",
        "run_code": "code.run",
        "create_word_document": "document.create_word",
        "create_pdf_document": "document.create_pdf",
        "document_creator": "document.creator",
        "generate_walkthrough": "document.walkthrough",
        "memory_save": "memory.save",
        "memory_get": "memory.get",
        "memory_search": "memory.search",
        "memory_delete": "memory.delete",
    }

    # Semantic Aliases (Preserve original semantic meaning without destructive rewriting)
    SEMANTIC_ALIASES: Dict[str, str] = {
        "open_browser": "browser_open_url",
        "web_browser": "browser_open_url",
        "browse_url": "browser_open_url",
        "click_element": "browser_click",
        "type_text": "browser_type",
        "read_file": "file_read",
        "write_file": "file_write",
        "delete_file": "file_delete",
        "list_files": "file_list",
        "list_directory": "file_list",
        "search_files": "file_search",
        "system_settings": "computer_settings",
        "set_setting": "computer_settings",
        "launch_app": "open_app",
        "start_app": "open_app",
        "execute_code": "run_code",
        "run_python": "run_code",
        "save_memory": "memory_save",
        "get_memory": "memory_get",
        "search_memory": "memory_search",
        "delete_memory": "memory_delete",
        "doc_creator": "document_creator",
        "make_document": "document_creator",
        "create_doc": "document_creator",
    }

    # Deprecated Tools & Guidance
    DEPRECATIONS: Dict[str, str] = {
        "file_controller": "Use specific atomic tools: 'file_read', 'file_write', 'file_list', or 'file_delete'.",
        "system_control": "Use 'computer_settings' for OS controls or 'cli_controller' for shell execution.",
        "browser_control": "Use 'browser_open_url' with real Playwright browser automation.",
    }

    @classmethod
    def resolve(
        cls,
        requested_name: str,
        catalog: Dict[str, ToolDefinition],
    ) -> Tuple[Optional[ToolDefinition], Optional[str], Optional[ToolErrorCode]]:
        """
        Resolve a requested tool identifier against the catalog.
        Returns (resolved_definition, error_message, error_code).
        """
        raw_name = str(requested_name or "").strip()
        if not raw_name:
            return None, "Empty tool name requested.", ToolErrorCode.INVALID_ARGUMENT

        # Strip version tag if present (e.g. "file_write:v1" -> "file_write")
        name_only = raw_name.split(":")[0].strip()

        # 1. Exact Name Match in Catalog
        if name_only in catalog:
            return catalog[name_only], None, None

        # 2. Namespaced ID Match in Catalog
        for def_obj in catalog.values():
            if def_obj.tool_id == name_only or def_obj.tool_id.endswith(f".{name_only}"):
                return def_obj, None, None

        # 3. Direct Canonical Namespace Lookup
        if name_only in cls.NAMESPACE_MAP:
            target_flat = name_only
            target_ns = cls.NAMESPACE_MAP[name_only]
            if target_flat in catalog:
                return catalog[target_flat], None, None
            for def_obj in catalog.values():
                if def_obj.tool_id == target_ns:
                    return def_obj, None, None

        # 4. Reverse Namespace Lookup (e.g. requested "filesystem.write" -> resolves to "file_write")
        for flat, ns in cls.NAMESPACE_MAP.items():
            if ns == name_only and flat in catalog:
                return catalog[flat], None, None

        # 5. Semantic Alias Lookup
        alias_target = cls.SEMANTIC_ALIASES.get(name_only.lower())
        if alias_target and alias_target in catalog:
            logger.debug(f"Resolved semantic alias '{name_only}' -> '{alias_target}'")
            return catalog[alias_target], None, None

        # 6. Deprecation Notice Check
        if name_only in cls.DEPRECATIONS:
            guidance = cls.DEPRECATIONS[name_only]
            return None, f"Tool '{name_only}' is deprecated. {guidance}", ToolErrorCode.TOOL_NOT_FOUND

        return None, f"Tool '{name_only}' was not found in the capability registry.", ToolErrorCode.TOOL_NOT_FOUND
