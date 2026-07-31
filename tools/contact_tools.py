# tools/contact_tools.py — BR-Jarvis Contact Import & Management Tools
"""
Contact Management & Mobile Import Tools Plugin for JARVIS.
Exposes tools to:
- Import mobile contacts (.vcf vCard files, CSV files, or raw content)
- Add, search, and list stored contacts
- Resolve contact names/aliases ("Mom", "Boss") to phone numbers and email addresses.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from tools.registry import register_tool
from memory.contact_manager import get_contact_store


@register_tool(
    name="import_contacts",
    description="Import mobile contacts from a vCard (.vcf) file or CSV (.csv) file path or raw text content.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or workspace-relative path to .vcf or .csv contact file"},
            "content": {"type": "string", "description": "Raw vCard or CSV text content (optional if file_path is provided)"},
            "format": {"type": "string", "enum": ["vcf", "csv", "auto"], "description": "Format specification (defaults to auto-detect)"}
        }
    }
)
def tool_import_contacts(args: dict) -> str:
    """Import contacts from vCard or CSV."""
    if isinstance(args, str):
        path_str = args.strip()
        content = ""
        fmt = "auto"
    else:
        path_str = str(args.get("file_path") or args.get("path") or args.get("file") or "").strip()
        content = str(args.get("content") or "").strip()
        fmt = str(args.get("format") or "auto").lower().strip()

    store = get_contact_store()

    if path_str:
        p = Path(path_str)
        if p.exists() and p.is_file():
            ext = p.suffix.lower()
            if ext == ".vcf" or fmt == "vcf":
                res = store.import_vcf(p)
                return f"📱 Imported vCard contacts: {res['imported_new']} new, {res['updated']} updated. Total contacts: {res['total_store']}."
            elif ext == ".csv" or fmt == "csv":
                res = store.import_csv(p)
                return f"📱 Imported CSV contacts: {res['imported_new']} new, {res['updated']} updated. Total contacts: {res['total_store']}."
            else:
                # Try vcf then csv
                res = store.import_vcf(p)
                if res.get("imported_new", 0) == 0 and res.get("updated", 0) == 0:
                    res = store.import_csv(p)
                return f"📱 Imported contacts from file: {res.get('imported_new', 0)} new, {res.get('updated', 0)} updated. Total contacts: {res.get('total_store', 0)}."
        else:
            return f"Error: Contact file not found at '{path_str}'."

    if content:
        if "BEGIN:VCARD" in content.upper() or fmt == "vcf":
            res = store.import_vcf(content)
        else:
            res = store.import_csv(content)
        return f"📱 Imported contacts from text content: {res['imported_new']} new, {res['updated']} updated. Total contacts: {res['total_store']}."

    return "Error: Provide either 'file_path' or 'content' to import contacts."


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
            "aliases": {"type": "array", "items": {"type": "string"}, "description": "Aliases/nicknames (e.g. ['Mom', 'Mother'])"},
            "query": {"type": "string", "description": "Search query for 'search' action"}
        },
        "required": ["action"]
    }
)
def tool_manage_contacts(args: dict) -> str:
    """Manage stored contacts."""
    if isinstance(args, str):
        action = args.strip().lower()
    else:
        action = str(args.get("action") or "list").strip().lower()

    store = get_contact_store()

    if action in ("add", "save", "create"):
        name = str(args.get("name") or "").strip()
        phone = str(args.get("phone_number") or args.get("phone") or "").strip()
        email = str(args.get("email") or "").strip()
        raw_aliases = args.get("aliases") or []
        aliases = [str(a).strip() for a in raw_aliases if str(a).strip()] if isinstance(raw_aliases, list) else []

        if not name:
            return "Error: 'name' is required for adding a contact."

        data = store.add_contact(name=name, phone_number=phone, email=email, aliases=aliases)
        return f"👤 Contact saved: '{data['name']}' (Phone: '{data['phone_number']}', Email: '{data['email']}')."

    elif action in ("list", "show", "get"):
        contacts = store.search_contacts("")
        if not contacts:
            return "📱 No contacts saved yet. Use 'import_contacts' or 'manage_contacts' (action='add') to add contacts."
        
        output = [f"📱 Saved Contacts ({len(contacts)} total):"]
        for c in contacts[:30]:
            alias_str = f" (Aliases: {', '.join(c['aliases'])})" if c.get("aliases") else ""
            output.append(f"  • {c['name']} — Phone: {c.get('phone_number','N/A')} | Email: {c.get('email','N/A')}{alias_str}")
        if len(contacts) > 30:
            output.append(f"  ... and {len(contacts)-30} more contacts.")
        return "\n".join(output)

    elif action in ("search", "find"):
        q = str(args.get("query") or args.get("name") or "").strip()
        results = store.search_contacts(q)
        if not results:
            return f"No contacts matching '{q}' found."
        
        output = [f"🔍 Search results for '{q}' ({len(results)} found):"]
        for c in results:
            output.append(f"  • {c['name']} — Phone: {c.get('phone_number','N/A')} | Email: {c.get('email','N/A')}")
        return "\n".join(output)

    return f"Unknown action '{action}'. Supported actions: 'add', 'list', 'search'."


@register_tool(
    name="resolve_contact",
    description="Look up phone number, email address, or WhatsApp target by contact name or alias (e.g. 'Mom', 'John').",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Contact name, nickname, alias, or phone number"}
        },
        "required": ["name"]
    }
)
def tool_resolve_contact(args: dict) -> str:
    """Resolve a contact name to target info."""
    name_str = args if isinstance(args, str) else str(args.get("name") or args.get("query") or "").strip()
    if not name_str:
        return "Error: Provide a contact name to resolve."

    store = get_contact_store()
    c = store.resolve_name(name_str)

    if not c:
        return f"Contact '{name_str}' not found in contact store. Use 'import_contacts' to import mobile contacts."

    return (
        f"👤 Resolved Contact '{c['name']}':\n"
        f"  • Phone: {c.get('phone_number', 'Not provided')}\n"
        f"  • Email: {c.get('email', 'Not provided')}\n"
        f"  • Aliases: {', '.join(c.get('aliases', []))}"
    )
