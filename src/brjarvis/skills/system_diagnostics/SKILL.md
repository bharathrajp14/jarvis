---
name: system_diagnostics
description: System diagnostics, CPU/RAM process telemetry, and frozen task terminator skill.
category: general
domain: OS & System Diagnostics
allowed-tools: [get_system_diagnostics, system_diagnostic, system_cleanup, system_optimizer, kill_process]
triggers: [/sys-diag, /kill-task, /check-health, system diagnostics, kill process]
user-invocable: true
---

# ⚙️ System Diagnostics & Process Manager Skill

Use this skill whenever the user requests checking system health, CPU/RAM usage, memory hogs, or killing stuck processes.

## Execution Protocol:

1. **Telemetry & Resource Inspection**:
   - Call `get_system_diagnostics` or `system_diagnostic` to retrieve real-time CPU %, RAM usage, disk space, and top resource-consuming processes.
2. **System Health Evaluation**:
   - Identify abnormal memory spikes or frozen background jobs.
3. **Targeted Process Termination**:
   - If a stuck process is identified, call `kill_process(identifier="<name_or_pid>")` to safely terminate the process.
4. **Health Summary**:
   - Report active CPU %, available RAM, and action results.
