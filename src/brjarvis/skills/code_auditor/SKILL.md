---
name: code_auditor
description: Automated codebase AST analysis, dead-code detection, syntax compilation check, and quality audit engine.
category: engineering
domain: Code Quality & Audit
allowed-tools: [audit_codebase, audit_prompt_security, code_refactor, file_list, file_read, run_code]
triggers: [/code-audit, /audit-codebase, /ast-audit, audit codebase]
user-invocable: true
---

# 🛡️ Codebase Quality & AST Auditor Skill

Use this skill whenever the user requests a code quality audit, AST syntax tree analysis, dead-code scan, or architectural review of the repository.

## Execution Protocol:

1. **Workspace AST & Syntax Scan**:
   - Invoke `audit_codebase(target_dir=".")` to analyze all Python/TS/JS modules for compilation validity and syntax health.
2. **Security Anti-Pattern Check**:
   - Check for hazardous patterns such as unvalidated `eval()`, hardcoded credentials, and bare `except:` blocks.
3. **AST Structure & Complexity**:
   - Use `code_refactor(action="analyze_ast", ...)` or `file_read` to inspect cyclomatic complexity and large functions (>50 lines).
4. **Structured Audit Deliverable**:
   Generate an executive summary:
   ```markdown
   # 🛡️ Codebase Audit Report
   - **Total Files Scanned**: <count>
   - **Overall Health Score**: <score>/100
   - **Syntax & Compilation Status**: [PASS / FAIL]

   ### 🔍 Findings & Refactoring Opportunities
   | Severity | File:Line | Finding | Recommended Fix |
   | :--- | :--- | :--- | :--- |
   | 🔴 CRITICAL | `src/module.py:45` | Unsafe pattern | Solution |
   | 🟡 WARNING | `src/utils.py:120` | High complexity | Solution |
   ```
