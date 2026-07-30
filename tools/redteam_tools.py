# tools/redteam_tools.py — JARVIS MK37 Red Team Scoped Tools Plugin
"""
Red team security tools plugin for JARVIS MK37.
Exposes scoped OSINT, port scanning, header audits, and report generation.
"""
from __future__ import annotations

import json
from pathlib import Path
from tools.registry import register_tool


def _get_scope_enforcer():
    scope_path = Path(__file__).resolve().parent.parent / "current_scope.json"
    if scope_path.exists():
        from redteam.scope import ScopeEnforcer
        return ScopeEnforcer(str(scope_path))
    return None


def _get_recon_engine():
    scope = _get_scope_enforcer()
    if scope:
        from redteam.recon import ReconEngine
        return ReconEngine(scope)
    return None


def _get_vuln_scanner():
    scope = _get_scope_enforcer()
    if scope:
        from redteam.vuln_scanner import VulnScanner
        return VulnScanner(scope)
    return None


@register_tool(
    name="port_scan",
    description="Scan TCP ports on a host (scope-checked). Returns open/closed status.",
    parameters={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Target host IP or hostname"},
            "ports": {"type": "array", "items": {"type": "integer"}, "description": "List of port numbers (default: common ports)"},
        },
        "required": ["host"],
    }
)
def tool_port_scan(args: dict) -> str:
    recon = _get_recon_engine()
    if not recon:
        return "ERROR: No scope file loaded. Cannot run scoped tools."
    host = str(args.get("host") or args.get("ip") or args.get("target") or "").strip()
    if not host:
        return "ERROR: 'host' parameter is required for port_scan."
    result = recon.port_scan(host, args.get("ports"))
    return json.dumps(result, indent=2)


@register_tool(
    name="dns_enum",
    description="Enumerate DNS records for a domain (scope-checked).",
    parameters={
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain"},
        },
        "required": ["domain"],
    }
)
def tool_dns_enum(args: dict) -> str:
    recon = _get_recon_engine()
    if not recon:
        return "ERROR: No scope file loaded."
    domain = str(args.get("domain") or args.get("host") or args.get("target") or "").strip()
    if not domain:
        return "ERROR: 'domain' parameter is required for dns_enum."
    result = recon.dns_enum(domain)
    return json.dumps(result, indent=2)


@register_tool(
    name="headers_audit",
    description="Audit HTTP security headers of a URL (scope-checked).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL"},
        },
        "required": ["url"],
    }
)
def tool_headers_audit(args: dict) -> str:
    recon = _get_recon_engine()
    if not recon:
        return "ERROR: No scope file loaded."
    url = str(args.get("url") or args.get("uri") or args.get("link") or "").strip()
    if not url:
        return "ERROR: 'url' parameter is required for headers_audit."
    result = recon.headers_audit(url)
    return json.dumps(result, indent=2)


@register_tool(
    name="whois_lookup",
    description="Perform a WHOIS lookup on a domain (scope-checked).",
    parameters={
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain"},
        },
        "required": ["domain"],
    }
)
def tool_whois_lookup(args: dict) -> str:
    recon = _get_recon_engine()
    if not recon:
        return "ERROR: No scope file loaded."
    domain = str(args.get("domain") or args.get("host") or args.get("target") or "").strip()
    if not domain:
        return "ERROR: 'domain' parameter is required for whois_lookup."
    return recon.whois(domain)


@register_tool(
    name="nmap_scan",
    description="Run an nmap service scan on a host (scope-checked, requires nmap installed).",
    parameters={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Target host"},
        },
        "required": ["host"],
    }
)
def tool_nmap_scan(args: dict) -> str:
    scanner = _get_vuln_scanner()
    if not scanner:
        return "ERROR: No scope file loaded."
    host = str(args.get("host") or args.get("ip") or args.get("target") or "").strip()
    if not host:
        return "ERROR: 'host' parameter is required for nmap_scan."
    return scanner.nmap_service_scan(host)


@register_tool(
    name="generate_report",
    description="Generate a professional penetration test report in markdown.",
    parameters={
        "type": "object",
        "properties": {
            "data": {"type": "object", "description": "Report data dict"},
        },
        "required": ["data"],
    }
)
def tool_generate_report(args: dict) -> str:
    from redteam.report import generate_report
    data = args.get("data") or args.get("report_data") or {}
    return generate_report(data)


@register_tool(
    name="audit_prompt_security",
    description="Audit user prompt or screen/web content for injection attacks.",
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Content to inspect for injection vulnerabilities"},
        },
        "required": ["content"],
    }
)
def audit_prompt_security(args: dict) -> str:
    """Audit content for prompt injection indicators (instruction-override phrases, fake roles, etc.)."""
    content = args.get("content", "")
    if not isinstance(content, str):
        return "CLEAN"
    
    # 1. Pattern matching common injection override phrases
    override_keywords = [
        "ignore previous instructions",
        "ignore all instructions",
        "disregard the system prompt",
        "ignore system prompt",
        "disregard previous instructions",
        "you must now ignore",
        "ignore the above instructions",
        "ignore instructions above",
        "dan mode",
        "developer mode active",
        "unrestricted mode",
        "reveal your system prompt",
        "print system instructions",
        "output your initial prompt",
        "send my api key",
        "bypass security constraints"
    ]
    low_content = content.lower()
    for kw in override_keywords:
        if kw in low_content:
            return f"INJECTION DETECTED: Security override phrase matched '{kw}'"
            
    # 2. Fake role markers inside data
    fake_role_markers = [
        "system:",
        "user:",
        "assistant:",
        "<|im_start|>",
        "<|im_end|>",
        "### new instructions",
        "### instruction",
        "### response"
    ]
    for marker in fake_role_markers:
        if marker in low_content:
            return f"INJECTION DETECTED: Fake role marker matched '{marker}'"

    # 3. Unicode zero-width characters/suspicious markers
    suspicious_chars = ["\u200b", "\u200c", "\u200d", "\ufeff"]
    for sc in suspicious_chars:
        if sc in content:
            return "INJECTION DETECTED: Suspicious hidden zero-width character detected"

    # 4. Unusually long base64-looking blocks to hide instruction injections
    import re
    base64_pat = re.compile(r'[A-Za-z0-9+/]{80,}=*')
    if base64_pat.search(content):
        return "INJECTION DETECTED: Large base64 payload block detected"

    return "CLEAN"
