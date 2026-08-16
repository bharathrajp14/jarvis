---
name: code_doctor
description: Autonomous workspace code diagnostician, lint repairer, and self-healing engine.
category: engineering
domain: Code Healing & Debugging
allowed-tools: [run_code, file_read, file_write, batch_file_ops, code_refactor, open_workspace_file]
triggers: [/code-doctor, /self-heal, /fix-code, fix broken tests, repair bugs]
user-invocable: true
---

# 🩺 Autonomous Code Doctor & Self-Healing Skill

When the user asks to diagnose bugs, fix broken modules, resolve test failures, or run repository self-healing:

## Execution Protocol:

1. **Compilation & Test Failure Discovery**:
   - Run `run_code(code="import pytest; pytest.main(['-q', '--tb=short'])")` or execute test commands to discover failing assertions and tracebacks.
2. **Root-Cause Pinpointing**:
   - Read the failing source files with `file_read`.
   - Inspect line numbers, symbol definitions, and variable states.
3. **Surgical Patching**:
   - Apply minimal, robust fixes using `file_write` or `batch_file_ops` without collateral regressions.
   - Avoid deleting working code or adding unneeded dependencies.
4. **Empirical Verification**:
   - Re-run the test suite with `run_code` to verify 100% green pass rate across all tests.
   - Summarize the bug cause and exact modifications made.
