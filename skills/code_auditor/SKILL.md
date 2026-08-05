---
name: code_auditor
description: Automated codebase quality, structure, and coding standards verification skill.
---

# 🛡️ Skill: Codebase Security & Quality Auditor

Use this skill whenever the user requests a security scan, syntax check, or quality audit of the codebase.

## Workflow:

1. Call `audit_codebase` passing `target_dir="."`.
2. Inspect AST syntax compilation and potential security pattern findings (`eval()`, hardcoded secrets).
3. Report findings clearly in markdown summary.
