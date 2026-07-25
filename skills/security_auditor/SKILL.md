---
name: security_auditor
description: Autonomous project security auditor, hardcoded secret scanner, and permissions policy validator.
user_invocable: true
---

# 🛡️ Autonomous Security Auditor Skill

When the user asks to run security audits, scan for leaked API keys, or inspect permissions:

## Execution Steps:
1. **Secret & Key Exposure Scan**: Search for hardcoded `API_KEY`, `token`, `secret`, `password` strings using `file_search` or regex scanning across workspace files.
2. **Permission Policy Audit**: Verify that permissions in `permissions.py` are set to `AUTO_ALLOW` or `STRICT` as intended.
3. **Environment Security**: Verify that `.env` is listed in `.gitignore` and credentials are stored securely in `config/api_keys.json`.
4. **Audit Report**: Provide a concise markdown table summarizing security compliance state and any remediations applied.
