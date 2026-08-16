---
name: system_diagnostics
description: System diagnostics, process telemetry, and task killer skill.
---

# ⚙️ Skill: System Diagnostics & Task Killer

Use this skill whenever the user requests checking system health, CPU/RAM usage, memory hogs, or killing stuck processes.

## Workflow:

1. **Telemetry Inspection**: Call `get_system_diagnostics` to get real-time CPU, RAM, disk, and top 10 memory-hogging processes.
2. **Process Termination**: Call `kill_process` with `identifier="notepad.exe"` or `identifier="1234"` to terminate frozen tasks.
