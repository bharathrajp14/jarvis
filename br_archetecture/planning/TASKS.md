# 📋 BR JARVIS — Comprehensive Project Task Backlog

> **Document Status**: Active Production Task Backlog  
> **Scope**: Feature Engineering, Bug Resolutions, Modular Refactoring, Security Hardening, & Multi-Agent Swarm  
> **Last Updated**: July 2026 (MK37.31.0 Release & Active Maintenance Backlog)  

---

## 📊 Task Overview & Status Tracker

| Category | Total Tasks | Completed | Pending | Priority Summary |
|---|---|---|---|---|
| 🚀 **MK37 Core Upgrades** | 12 | 12 | 0 | All P0/P1 Completed ✅ |
| 🔴 **Active Bug Fixes (BUG-001 to BUG-012)** | 12 | 12 | 0 | All P0/P1 Resolved & Verified ✅ |
| 🧠 **Phase 7: Advanced Autonomy & Swarm** | 4 | 0 | 4 | 2 High (P0), 2 Medium (P1) |
| 🧹 **Phase 8: Modularization & Tech Debt** | 4 | 0 | 4 | 2 High (P0), 2 Medium (P1) |
| 🛡️ **Phase 9: Security & Autonomy Audit** | 3 | 0 | 3 | 1 High (P0), 2 Medium (P1) |

---

## 🚀 Completed MK37 Architectural Tasks (100% Verified)

### Task MK37.9: ONNX Silero Voice Activity Detection Subsystem
- **Status**: `COMPLETED` ✅ | `voice/silero_vad.py`
- **Deliverables**: ONNX Silero VAD integration (<10ms latency) eliminating background silence noise & audio clipping.

### Task MK37.10: Zero-Disk Whisper In-Memory Byte Streaming & Silence Gate
- **Status**: `COMPLETED` ✅ | `voice/whisper_local.py`
- **Deliverables**: Direct in-memory byte buffer ASR streaming with RMS silence gate and post-inference hallucination filter.

### Task MK37.11: CDP Chrome/Edge Browser DOM Bridge Vision Tier
- **Status**: `COMPLETED` ✅ | `vision/dom_bridge.py`
- **Deliverables**: Tier 2 CDP DevTools Protocol accessibility DOM inspection bridge for instant element extraction.

### Task MK37.12: 94-Test Automated Verification Suite
- **Status**: `COMPLETED` ✅ | `tests/`
- **Deliverables**: 100% pass rate across 94 unit & integration tests (`pytest tests/`).

### Task MK37.1: Multi-Backend Clipboard Engine
- **Status**: `COMPLETED` ✅ | `actions/clipboard_utils.py`
- **Deliverables**: 5-layer prioritized fallback (`pyperclip` -> Win32 `ctypes` -> `tkinter` -> PowerShell -> CLI).

### Task MK37.2: Antigravity Scratchpad Subsystem & Tools
- **Status**: `COMPLETED` ✅ | `agent/scratchpad.py` | `tools/scratchpad_tools.py`
- **Deliverables**: `./scratch/` workspace isolation; `scratchpad_eval` multi-language script execution.

### Task MK37.3: Autonomous Planning Mode & GFM Artifact Engine
- **Status**: `COMPLETED` ✅ | `agent/planning_mode.py` | `agent/artifacts.py`
- **Deliverables**: `warrants_plan` classifier; `implementation_plan.md` & `walkthrough.md` generation.

### Task MK37.4: Trajectory Transcripts Logging
- **Status**: `COMPLETED` ✅ | `agent/transcript_logger.py`
- **Deliverables**: JSON Lines trajectory logger (`transcript.jsonl`) integrated into ReAct chat loop.

### Task MK37.5: Voice Prompt Refinement Engine
- **Status**: `COMPLETED` ✅ | `voice/prompt_refiner.py`
- **Deliverables**: Vocal hesitation cleaner, domain vocabulary mapping, transparent raw vs refined UI logging.

### Task MK37.6: Multi-Task & Sub-Agent Frontend Dashboard
- **Status**: `COMPLETED` ✅ | `ui.py`
- **Deliverables**: Dedicated **"🚀 Multi-Tasks"** tab; Task Cards with status badges and progress bars.

### Task MK37.7: Conscious Step Planner & Adaptive Flexible Step Budget
- **Status**: `COMPLETED` ✅ | `agent/step_planner.py`
- **Deliverables**: Conscious sub-step goal decomposition & progress velocity step extensions.

---

## 🔴 Active Bug Fix Backlog (BUG-001 to BUG-010)

### Task BUG-001: Fix Startup Crash `self.ui` AttributeError
- **Priority**: `P0` (High) | `voice/assistant.py`
- **Goal**: Re-add missing `self.ui = ui` assignment in `BRVoiceAssistant.__init__()`.

### Task BUG-002: Migrate `asyncio.get_event_loop()` to `get_running_loop()`
- **Priority**: `P0` (High) | `core/`, `server.py`
- **Goal**: Eliminate Python 3.14 deprecation warnings and event loop crashes.

### Task BUG-003: ReAct Orchestrator Loop Infinite-Loop Guard
- **Priority**: `P0` (High) | `orchestrator.py`
- **Goal**: Implement tool call deduplication to break infinite loops when tool parameters repeat.

### Task BUG-004: Fix `_run_async` Deadlock in Tool Registry
- **Priority**: `P0` (High) | `tools/registry.py`
- **Goal**: Refactor `run_coroutine_threadsafe` to prevent thread deadlocks on async tools.

### Task BUG-005: SQLite WAL Mode & Connection Pool Sharing
- **Priority**: `P1` (Medium) | `memory/`
- **Goal**: Enable WAL mode and shared connection pooling across memory SQLite databases to prevent lock contention.

### Task BUG-006: Asynchronous Non-Blocking WebSocket Broadcast
- **Priority**: `P1` (Medium) | `server.py`
- **Goal**: Convert WSBroadcastStream to an async queue to prevent stdout blocking on slow clients.

### Task BUG-007: Lazy Tool & Action Plugin Loading
- **Priority**: `P1` (Medium) | `tools/registry.py`
- **Goal**: Lazy-load plugins on first call to eliminate 5-15 second startup import storm.

### Task BUG-008: Decompose `ui.py` 72KB Monolith
- **Priority**: `P1` (Medium) | `ui.py` -> `ui/`
- **Goal**: Refactor `ui.py` into modular tab components (`ui/tabs/chat.py`, `ui/tabs/tasks.py`, `ui/tabs/settings.py`).

### Task BUG-009: Remove Hardcoded API Key Fallback
- **Priority**: `P1` (Medium) | `backends/gemini.py`
- **Goal**: Remove hardcoded API key fallback string from source code.

### Task BUG-010: Synchronize Tool Name Alias Registry
- **Priority**: `P2` (Low) | `agent/executor.py`
- **Goal**: Update tool alias mapping dictionary to cover newly added tools.
