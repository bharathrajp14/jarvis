---
name: code_doctor
description: Autonomous workspace code diagnostician, lint repairer, and syntax tree verification engine.
user_invocable: true
---

# 🩺 Autonomous Code Doctor & Self-Healing Skill

When the user asks to diagnose bugs, fix broken modules, or run project self-healing:

## Execution Steps:
1. **Workspace Compilation Audit**: Run `run_code` with `py_compile` or `pytest` to locate exact syntax errors and broken imports.
2. **AST & Type Inspection**: View broken files with `file_read` to trace line numbers and inspect symbol definitions.
3. **Targeted Code Patching**: Use `file_write` or `replace_file_content` to apply minimal, robust fixes without collateral code churn.
4. **Empirical Verification**: Re-run `pytest` test suite to verify 100% green pass status across all tests.
