# 🧹 BR JARVIS — Technical Debt & Refactoring Audit

> **Document Status**: Production Architecture Specification  
> **Scope**: Codebase Debt Audits, Refactoring Targets & Maintenance Roadmap  
> **Version**: MK37.31.0  

---

## 1. Executive Debt Audit Overview

The BR JARVIS MK37 codebase (~180 Python files, 30+ packages) achieves a **100% test pass rate** across all 94 Pytest verification tests (`pytest tests/`). Full project analysis reveals key technical debt targets that are actively being refactored and optimized.

---

## 2. Identified Technical Debt & Refactoring Targets

### 1. `ui.py` Monolith File Breakdown (72KB / 2000+ Lines)
- **Issue**: The entire Tkinter desktop interface — HUD animations, chat log, settings panels, face canvas rendering, waveform visualizer, and Multi-Task dashboard — resides in a single 72KB file.
- **Refactoring Strategy**: Modularize `ui.py` into dedicated sub-packages under `ui/`:
  - `ui/tabs/chat_tab.py`: Chat stream & message rendering.
  - `ui/tabs/tasks_tab.py`: Glossy Multi-Task cards & progress bars.
  - `ui/tabs/settings_tab.py`: API keys & system settings dialogs.
  - `ui/widgets/canvas_hud.py`: Face canvas & waveform HUD visualizers.

### 2. Concurrent SQLite Database Lock Contention (`memory/`) [RESOLVED]
- **Status**: ✅ **RESOLVED in v37.31.0**
- **Fix**: Enabled SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), increased busy timeouts (`PRAGMA busy_timeout=20000;`), and set `timeout=20.0` across `memory/lessons.py` and `memory/conversation_store.py`.

### 3. Tool & Action Import Storm Optimization (`tools/registry.py`)
- **Issue**: Initial invocation of `tools/registry.py` eagerly imports all 34 tool modules and 34 action modules, causing a 5–15 second startup stall.
- **Refactoring Strategy**: Implement lazy module loading on first tool call request.

### 4. `asyncio.get_event_loop()` Python 3.14 Deprecation [RESOLVED]
- **Status**: ✅ **RESOLVED in v37.31.0**
- **Fix**: Replaced legacy `asyncio.get_event_loop()` calls with `asyncio.get_running_loop()` and `asyncio.get_event_loop_policy().get_event_loop()` across `voice/assistant.py` and `core/lifecycle.py`.

### 5. Synchronous WebSocket Broadcast Queue (`server.py`)
- **Issue**: `WSBroadcastStream` broadcasts stdout to WebSocket clients synchronously; slow or disconnected clients can block process stdout.
- **Refactoring Strategy**: Replace direct WebSocket sends with an asynchronous non-blocking background queue (`asyncio.Queue`).
