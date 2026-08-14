# security/sanitizer.py — Deterministic Input, Shell & Prompt Injection Sanitizer
"""
Deterministic Input & Prompt Injection Sanitizer for BR JARVIS MK40.
Defangs untrusted external inputs from web scraping, PDFs, emails, and third-party data,
and detects shell metacharacter injection in command execution pipelines.
"""
from __future__ import annotations

import re
from typing import Tuple


class InputSanitizer:
    """Security sanitizer for commands, user inputs, and untrusted external data."""

    # Dangerous shell injection patterns
    SHELL_INJECTION_PATTERNS = [
        (re.compile(r';\s*(rm|del|format|rd|powershell|curl|nc|bash|sh)\b', re.IGNORECASE), "Command chaining delimiter (;) with hazardous executable"),
        (re.compile(r'\|\s*(curl|nc|powershell|bash|sh|wget)\b', re.IGNORECASE), "Pipe (|) exfiltration or remote execution"),
        (re.compile(r'(&&|\|\|)\s*(format|rm|del|powershell|Remove-Item)\b', re.IGNORECASE), "Logical operator chaining with destructive action"),
        (re.compile(r'`[^`]*`'), "Backtick command substitution"),
        (re.compile(r'\$\([^)]*\)'), "Subshell execution syntax $()"),
        (re.compile(r'\bformat\s+[a-zA-Z]:', re.IGNORECASE), "Disk format command"),
        (re.compile(r'\brm\s+-rf\s+/', re.IGNORECASE), "Root filesystem deletion"),
        (re.compile(r'powershell(?:\.exe)?\s+-(?:e|enc|encodedcommand)\b', re.IGNORECASE), "PowerShell base64 encoded command"),
        (re.compile(r'cmd(?:\.exe)?\s+/[cC]\s+start\b', re.IGNORECASE), "CMD nested process launcher"),
        (re.compile(r'python(?:\.exe)?\s+-c\s+.*?(?:socket|subprocess|os\.system)', re.IGNORECASE), "Python inline socket/subprocess execution"),
    ]

    # Prompt injection patterns in untrusted external text
    PROMPT_INJECTION_DEFANG_RULES = [
        (re.compile(r'\[\s*(SYSTEM|DEVELOPER|JARVIS)\s+INSTRUCTION\s*\]:?', re.IGNORECASE), "[EXTERNAL_TEXT_TAG]:"),
        (re.compile(r'<!--\s*JARVIS\s+OVERRIDE[^>]*-->', re.IGNORECASE), "[DEFANGED_HTML_COMMENT]"),
        (re.compile(r'\bSYSTEM\s+ALERT:', re.IGNORECASE), "NOTICE:"),
        (re.compile(r'\b(Ignore\s+all\s+previous\s+instructions|Ignore\s+previous\s+directives)\b', re.IGNORECASE), "[DEFANGED_PROMPT_DIRECTIVE]"),
        (re.compile(r'^(Assistant|System|Human):\s*', re.IGNORECASE | re.MULTILINE), "[DATA]: "),
    ]

    @classmethod
    def validate_shell_safety(cls, command: str) -> Tuple[bool, str]:
        """Verify command does not contain dangerous shell metacharacters or privilege escalation."""
        if not command or not isinstance(command, str):
            return True, "Empty command"

        for pattern, reason in cls.SHELL_INJECTION_PATTERNS:
            if pattern.search(command):
                return False, f"Dangerous pattern detected: {reason}"

        return True, "Clean"

    @classmethod
    def sanitize_external_data(cls, raw_text: str) -> str:
        """Defang prompt-injection and system-instruction overrides in external text."""
        if not raw_text or not isinstance(raw_text, str):
            return ""

        sanitized = raw_text
        for pattern, replacement in cls.PROMPT_INJECTION_DEFANG_RULES:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    @classmethod
    def sanitize_input(cls, user_input: str) -> str:
        """Sanitize general user input strings."""
        if not user_input or not isinstance(user_input, str):
            return ""
        return user_input.strip()
