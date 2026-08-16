# tools/contact_tools.py — BR-Jarvis Contact Import & Management Tools
"""
Contact Management & Mobile Import Tools Plugin for BR JARVIS MK40.2 / MK41.
Exposes tools to:
- Import mobile contacts (.vcf vCard files, CSV files, or raw content)
- Add, search, and list stored contacts
- Resolve contact names/aliases ("Mom", "Boss") to phone numbers and email addresses.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .domain import RiskLevel, SideEffectLevel, ToolCategory, ToolErrorCode, VerificationStrategy
from .registry import register_tool
from .tool_result import ToolResult
from memory.contact_manager import get_contact_store


@register_tool(
    name="import_contacts",
    description="Import mobile contacts from a vCard (.vcf) file or CSV (.csv) file path or raw text content.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or workspace-relative path to .vcf or .csv contact file"},
            "content": {"type": "string", "description": "Raw vCard or CSV text content"},
            "format": {"type": "string", "enum": ["vcf", "csv", "auto"], "description": "Format specification"},
        },
    },
    category="communication",
    risk_level="medium",
    permission_required="USER_WRITE",
    is_read_only=False,
    idempotent=True,
    verification_strategy="READ_BACK_VALUE",
)
def tool_import_contacts(args: dict) -> ToolResult:
    """Import contacts from vCard or CSV."""
    if isinstance(args, str):
        path_str = args.strip()
        content = ""
        fmt = "auto"
    else:
        path_str = str(args.get("file_path") or args.get("path") or "").strip()
        content = str(args.get("content") or "").strip()
        fmt = str(args.get("format") or "auto").lower().strip()

    store = get_contact_store()

    try:
        if path_str:
            p = Path(path_str)
            if not p.is_absolute():
                p = Path.cwd() / p
            if p.exists() and p.is_file():
                ext = p.suffix.lower()
                if ext == ".vcf" or fmt == "vcf":
                    res = store.import_vcf(p)
                elif ext == ".csv" or fmt == "csv":
                    res = store.import_csv(p)
                else:
                    res = store.import_vcf(p)
                    if res.get("imported_new", 0) == 0 and res.get("updated", 0) == 0:
                        res = store.import_csv(p)

                evidence = f"Imported contacts from file '{p.name}': {res.get('imported_new', 0)} new, {res.get('updated', 0)} updated. Total contacts: {res.get('total_store', 0)}."
                return ToolResult.success(
                    tool_name="import_contacts",
                    data=res,
                    output=f"📱 {evidence}",
                    evidence=evidence,
                    verified=True,
                    side_effects=[f"contacts:imported:{p.name}"],
                    metadata=res,
                )
            else:
                return ToolResult.failed(
                    "import_contacts",
                    ToolErrorCode.TOOL_NOT_FOUND,
                    f"Contact file not found at '{path_str}'.",
                )

        if content:
            if "BEGIN:VCARD" in content.upper() or fmt == "vcf":
                res = store.import_vcf(content)
            else:
                res = store.import_csv(content)
            evidence = f"Imported contacts from text: {res['imported_new']} new, {res['updated']} updated. Total contacts: {res['total_store']}."
            return ToolResult.success(
                tool_name="import_contacts",
                data=res,
                output=f"📱 {evidence}",
                evidence=evidence,
                verified=True,
                metadata=res,
            )

        return ToolResult.failed(
            "import_contacts",
            ToolErrorCode.INVALID_ARGUMENT,
            "Provide either 'file_path' or 'content' to import contacts.",
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="import_contacts",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to import contacts: {e}",
        )


@register_tool(
    name="manage_contacts",
    description="Add, list, or search contacts in JARVIS memory. Args: 'action' ('add', 'list', 'search'), 'name', 'phone_number', 'email', 'aliases', 'query'.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list", "search"], "description": "Action to perform"},
            "name": {"type": "string", "description": "Contact display name"},
            "phone_number": {"type": "string", "description": "Phone number with country code"},
            "email": {"type": "string", "description": "Email address"},
            "aliases": {"type": "array", "items": {"type": "string"}, "description": "Aliases or nicknames"},
            "query": {"type": "string", "description": "Search query for 'search' action"},
        },
        "required": ["action"],
    },
    category="communication",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=False,
)
def tool_manage_contacts(args: dict) -> ToolResult:
    """Manage stored contacts."""
    action = str(args.get("action") or "list").strip().lower()
    store = get_contact_store()

    try:
        if action in ("add", "save", "create"):
            name = str(args.get("name") or "").strip()
            phone = str(args.get("phone_number") or args.get("phone") or "").strip()
            email = str(args.get("email") or "").strip()
            raw_aliases = args.get("aliases") or []
            aliases = [str(a).strip() for a in raw_aliases if str(a).strip()] if isinstance(raw_aliases, list) else []

            if not name:
                return ToolResult.failed("manage_contacts", ToolErrorCode.INVALID_ARGUMENT, "'name' is required for adding a contact.")

            data = store.add_contact(name=name, phone_number=phone, email=email, aliases=aliases)
            evidence = f"Contact saved: '{data['name']}' (Phone: '{data['phone_number']}', Email: '{data['email']}')."
            return ToolResult.success(
                tool_name="manage_contacts",
                data=data,
                output=f"👤 {evidence}",
                evidence=evidence,
                verified=True,
                side_effects=[f"contact:added:{name}"],
                metadata=data,
            )

        elif action in ("list", "show", "get"):
            contacts = store.search_contacts("")
            evidence = f"Retrieved {len(contacts)} saved contacts."
            return ToolResult.success(
                tool_name="manage_contacts",
                data=contacts,
                output=json.dumps(contacts, indent=2),
                evidence=evidence,
                verified=True,
                metadata={"count": len(contacts)},
            )

        elif action in ("search", "find"):
            q = str(args.get("query") or args.get("name") or "").strip()
            results = store.search_contacts(q)
            evidence = f"Found {len(results)} contacts matching '{q}'."
            return ToolResult.success(
                tool_name="manage_contacts",
                data=results,
                output=json.dumps(results, indent=2),
                evidence=evidence,
                verified=True,
                metadata={"count": len(results), "query": q},
            )

        else:
            return ToolResult.failed(
                "manage_contacts",
                ToolErrorCode.INVALID_ARGUMENT,
                f"Unknown action '{action}'. Supported: 'add', 'list', 'search'.",
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="manage_contacts",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error managing contacts: {e}",
        )


@register_tool(
    name="resolve_contact",
    description="Look up phone number, email address, or WhatsApp target by contact name or alias (e.g. 'Mom', 'John').",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Contact name, nickname, or alias"},
        },
        "required": ["name"],
    },
    category="communication",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_resolve_contact(args: dict) -> ToolResult:
    """Resolve a contact name to target info."""
    name_str = args if isinstance(args, str) else str(args.get("name") or args.get("query") or "").strip()
    if not name_str:
        return ToolResult.failed("resolve_contact", ToolErrorCode.INVALID_ARGUMENT, "Provide a contact name to resolve.")

    try:
        store = get_contact_store()
        c = store.resolve_name(name_str)

        if not c:
            return ToolResult.failed(
                "resolve_contact",
                ToolErrorCode.TOOL_NOT_FOUND,
                f"Contact '{name_str}' not found in contact store.",
            )

        evidence = f"Resolved Contact '{c['name']}' -> Phone: {c.get('phone_number')}, Email: {c.get('email')}"
        return ToolResult.success(
            tool_name="resolve_contact",
            data=c,
            output=evidence,
            evidence=evidence,
            verified=True,
            metadata=c,
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="resolve_contact",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to resolve contact: {e}",
        )
