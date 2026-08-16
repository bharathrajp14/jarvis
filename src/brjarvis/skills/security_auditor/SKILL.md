---
name: security_auditor
description: Autonomous project compliance, secret leak detection, and prompt injection security validator.
category: engineering
domain: Security & Compliance
allowed-tools: [audit_prompt_security, audit_codebase, file_search_semantic, file_read, run_code]
triggers: [/security-audit, /scan-secrets, /prompt-guard, run security scan]
user-invocable: true
---

# 🛡️ Autonomous Security Auditor Skill

When the user asks to run security audits, scan for leaked API keys, or inspect permissions and guardrails:

## Execution Protocol:

1. **Secret & Key Exposure Scan**:
   - Scan for hardcoded `API_KEY`, `token`, `secret`, and `password` strings across repository files using `audit_codebase` and regex search.
   - Verify `.env` is listed in `.gitignore`.
2. **Prompt Injection & Red-Team Audit**:
   - Invoke `audit_prompt_security` to evaluate prompt defenses against adversarial jailbreaks and data exfiltration.
3. **Execution Permissions Check**:
   - Verify that permissions in `permissions.py` are set to `AUTO_ALLOW` or `STRICT` as intended.
4. **Audit Deliverable**:
   - Provide a concise markdown table summarizing security compliance state and any remediations applied.
