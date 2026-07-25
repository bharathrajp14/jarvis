# 🧹 BR JARVIS — Technical Debt & Refactoring Audit

> **Document Status**: Production Architecture Specification  
> **Scope**: Codebase Debt Audits, Refactoring Targets & Maintenance Roadmap  
> **Version**: MK38.2.0  

---

## 1. Executive Debt Audit Overview

The BR JARVIS MK38 codebase (~185 Python files, 30+ packages) achieves a **100% test pass rate** across all 110 Pytest verification tests (`pytest tests/`). Full project analysis reveals key technical debt targets that are actively being refactored and optimized.

---

## 2. Identified Technical Debt & Refactoring Targets

### 1. `ui.py` Monolith File Breakdown (72KB / 2000+ Lines)
- **Issue**: The entire Tkinter desktop interface — HUD animations, chat log, settings panels, face canvas rendering, waveform visualizer, and Multi-Task dashboard — resides in a single 72KB file.
- **Refactoring Strategy**: Modularize `ui.py` into dedicated sub-packages under `ui/`:
  - `ui/tabs/chat_tab.py`: Chat stream & message rendering.
  - `ui/tabs/tasks_tab.py`: Glossy Multi-Task cards & progress bars.
  - `ui/tabs/settings_tab.py`: API keys & system settings dialogs.
  - `ui/widgets/canvas_hud.py`: Face canvas & waveform HUD visualizers.

### 2. Path Policy Permission Check Bypass (`permissions.py`) [RESOLVED]
- **Status**: ✅ **RESOLVED in v38.2.0**
- **Fix**: Updated `check_permission(tool_name, args)` to evaluate target path arguments against `TIER_2_PATTERNS` (`system32`, `.ssh`, `login data`, `id_rsa`, `.pem`), preventing unauthorized file access.

### 3. ReAct Working Memory Context Window Bloat (`orchestrator.py`) [RESOLVED]
- **Status**: ✅ **RESOLVED in v38.2.0**
- **Fix**: Truncated `tool_result` strings added to `working_memory` at line 508 to a maximum of 4000 characters with `[... output truncated for context efficiency ...]`.

### 4. Concurrent SQLite Database Lock Contention (`memory/`) [RESOLVED]
- **Status**: ✅ **RESOLVED in v37.31.0**
- **Fix**: Enabled SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), increased busy timeouts (`PRAGMA busy_timeout=20000;`), and set `timeout=20.0` across `memory/lessons.py` and `memory/conversation_store.py`.

### 5. `asyncio.get_event_loop()` Python 3.14 Deprecation [RESOLVED]
- **Status**: ✅ **RESOLVED in v37.31.0**
- **Fix**: Replaced legacy `asyncio.get_event_loop()` calls with `asyncio.get_running_loop()` and `asyncio.get_event_loop_policy().get_event_loop()` across `voice/assistant.py` and `core/lifecycle.py`.

### 5. Synchronous WebSocket Broadcast Queue (`server.py`)
- **Issue**: `WSBroadcastStream` broadcasts stdout to WebSocket clients synchronously; slow or disconnected clients can block process stdout.
- **Refactoring Strategy**: Replace direct WebSocket sends with an asynchronous non-blocking background queue (`asyncio.Queue`).
