# tools/telegram_tools.py — BR-Jarvis Telegram Messaging Tools Plugin
"""
Telegram Messaging Tools Plugin for JARVIS.

Registers the following tools in the JARVIS tool registry:
  - send_telegram              → Send immediate Telegram message to any contact/@username/chat_id
  - schedule_telegram_message → Schedule a future Telegram message
  - manage_telegram_contacts  → Add or list saved Telegram contacts
  - telegram_bot_info         → Check bot connection status and get bot link
  - telegram_get_updates      → Discover chat_ids from users who have messaged the bot
"""

from __future__ import annotations

from brjarvis.actions.telegram_automation import get_telegram_automation

from .registry import register_tool

# ── Tool 1: Send Telegram Message ─────────────────────────────────────────────


@register_tool(
    name="send_telegram",
    description=(
        "Send a Telegram message to any contact, @username, or chat_id. "
        "NEVER use open_app or run_code to send Telegram messages; ALWAYS use send_telegram. "
        "Supports saved contact names (e.g. 'Appa', 'Mom', 'John'), "
        "@usernames (e.g. '@johnsmith'), numeric chat_ids, "
        "and group/channel IDs. "
        "Requires TELEGRAM_BOT_TOKEN in .env (get it from @BotFather). "
        "Falls back to Telegram desktop app automation if no bot token is configured."
    ),
    parameters={
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": (
                    "Contact name (e.g. 'Appa'), @username (e.g. '@johnsmith'), or numeric chat_id (e.g. '123456789')"
                ),
            },
            "message": {
                "type": "string",
                "description": "Message content to send (supports Markdown formatting)",
            },
        },
        "required": ["recipient", "message"],
    },
)
def tool_send_telegram(args: dict) -> str:
    """Send a Telegram message to a recipient."""
    if isinstance(args, str):
        parts = args.split(":", 1)
        recipient = parts[0].strip() if parts else ""
        message = parts[1].strip() if len(parts) > 1 else args.strip()
    else:
        recipient = str(
            args.get("recipient")
            or args.get("to")
            or args.get("contact")
            or args.get("username")
            or args.get("chat_id")
            or args.get("target")
            or ""
        ).strip()
        message = str(args.get("message") or args.get("text") or args.get("body") or args.get("content") or "").strip()

    if not recipient or not message:
        return "❌ Error: Both 'recipient' and 'message' are required for send_telegram."

    tg = get_telegram_automation()
    return tg.send_message(recipient=recipient, message_text=message)


# ── Tool 2: Schedule Telegram Message ─────────────────────────────────────────


@register_tool(
    name="schedule_telegram_message",
    description=(
        "Schedule a Telegram message to be automatically sent to a contact at a "
        "specified future date/time. The message is queued and sent in the background "
        "even while JARVIS continues other work."
    ),
    parameters={
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "Contact name, @username, or chat_id",
            },
            "message": {
                "type": "string",
                "description": "Message content to send",
            },
            "send_at": {
                "type": "string",
                "description": (
                    "Target date/time string. Formats: '2026-08-01 09:00', '2026-08-01 09:00:00', '14:30', '9:00 AM'"
                ),
            },
        },
        "required": ["recipient", "message", "send_at"],
    },
)
def tool_schedule_telegram_message(args: dict) -> str:
    """Schedule a Telegram message for future delivery."""
    if isinstance(args, str):
        return "❌ Error: 'schedule_telegram_message' expects a JSON dictionary with recipient, message, and send_at."

    recipient = str(args.get("recipient") or args.get("to") or args.get("contact") or "").strip()
    message = str(args.get("message") or args.get("text") or args.get("body") or "").strip()
    send_at = str(args.get("send_at") or args.get("time") or args.get("date") or args.get("at") or "").strip()

    if not recipient or not message or not send_at:
        return "❌ Error: 'recipient', 'message', and 'send_at' are all required."

    tg = get_telegram_automation()
    return tg.schedule_message(recipient=recipient, message_text=message, send_at=send_at)


# ── Tool 3: Manage Telegram Contacts ──────────────────────────────────────────


@register_tool(
    name="manage_telegram_contacts",
    description=(
        "Add a new Telegram contact mapping (name → chat_id or @username) "
        "or list all saved Telegram contacts. "
        "Use 'add' to save a new contact, 'list' to see all saved contacts. "
        "A chat_id can be discovered using the telegram_get_updates tool."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list"],
                "description": "Action to perform: 'add' or 'list'",
            },
            "name": {
                "type": "string",
                "description": "Contact display name (e.g. 'Appa', 'John', 'Work Group')",
            },
            "chat_id": {
                "type": "string",
                "description": (
                    "Telegram chat_id (numeric, e.g. '123456789') or @username (e.g. '@johnsmith'). "
                    "Use telegram_get_updates to discover chat_ids."
                ),
            },
        },
        "required": ["action"],
    },
)
def tool_manage_telegram_contacts(args: dict | str) -> str:
    """Add or list saved Telegram contacts."""
    if isinstance(args, str):
        action = args.strip().lower()
        args_dict: dict = {}
    else:
        args_dict = args if isinstance(args, dict) else {}
        action = str(args_dict.get("action") or "list").strip().lower()

    tg = get_telegram_automation()

    if action in ("add", "save", "create"):
        name = str(args_dict.get("name") or args_dict.get("contact_name") or "").strip()
        chat_id = str(args_dict.get("chat_id") or args_dict.get("username") or args_dict.get("id") or "").strip()
        if not name or not chat_id:
            return "❌ Error: Both 'name' and 'chat_id' (or @username) are required to add a contact."
        return tg.add_contact(name=name, chat_id=chat_id)

    elif action in ("list", "show", "get"):
        contacts = tg.list_contacts()
        if not contacts:
            return (
                "📭 No saved Telegram contacts found.\n"
                "Use manage_telegram_contacts with action='add' to save contacts, "
                "or use telegram_get_updates to discover chat_ids."
            )
        lines = ["📇 SAVED TELEGRAM CONTACTS:"]
        for c_name, c_id in contacts.items():
            lines.append(f"  • {c_name.title()}: {c_id}")
        return "\n".join(lines)

    return "❌ Unknown action. Supported actions: 'add', 'list'."


# ── Tool 4: Telegram Bot Info ──────────────────────────────────────────────────


@register_tool(
    name="telegram_bot_info",
    description=(
        "Check the status of the configured Telegram bot and get a shareable link "
        "for contacts to initiate messaging. Validates the TELEGRAM_BOT_TOKEN. "
        "Use this to verify the bot is working correctly."
    ),
    parameters={
        "type": "object",
        "properties": {},
    },
)
def tool_telegram_bot_info(args: dict) -> str:
    """Return info about the configured Telegram bot."""
    tg = get_telegram_automation()
    return tg.get_bot_info()


# ── Tool 5: Telegram Get Updates (Discover Chat IDs) ──────────────────────────


@register_tool(
    name="telegram_get_updates",
    description=(
        "Fetch recent messages received by the Telegram bot to discover chat_ids "
        "of users who have interacted with it. "
        "Use this to find the numeric chat_id needed to add a contact or send a message. "
        "Users must first send any message (e.g. /start) to the bot on Telegram."
    ),
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent updates to fetch (default: 10, max: 100)",
            },
        },
    },
)
def tool_telegram_get_updates(args: dict) -> str:
    """Fetch recent bot updates to discover chat_ids."""
    limit = int(args.get("limit") or 10) if isinstance(args, dict) else 10
    limit = max(1, min(limit, 100))  # Clamp to valid range
    tg = get_telegram_automation()
    return tg.get_updates(limit=limit)
