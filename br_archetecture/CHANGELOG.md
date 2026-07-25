# 📜 BR JARVIS — Architectural Execution Changelog

All major architectural updates, subsystem additions, and core refactorings are recorded in this document.

## [37.31.0] — 2026-07-25

### Ultra-Fast Silero VAD Voice Subsystem & CDP DOM Bridge Infrastructure
- **Silero Voice Activity Detection (`voice/silero_vad.py`)**:
  - Integrated ONNX-based Silero VAD for low-latency acoustic speech chunk segmentation (<10ms inference overhead).
  - Eliminates silence clipping and background static noise triggers before passing speech buffers to Whisper ASR.
- **Zero-Disk Whisper Audio Streaming (`voice/whisper_local.py`)**:
  - Implemented direct in-memory audio byte stream processing without disk file I/O overhead.
  - Added RMS acoustic silence gating and post-inference hallucination filtering to eliminate phantom ASR transcriptions.
- **CDP DOM Bridge Vision Tier (`vision/dom_bridge.py`)**:
  - Tier 2 CDP Chrome/Edge Browser accessibility DOM inspection bridge allowing real-time tree extraction and visual grounding coordinate mapping without raw screenshot dependency.
- **Gemini Model Router Fallback Modernization (`backends/gemini.py`)**:
  - Updated model fallback list with `gemini-3.6-flash-high`, `gemini-3-flash-agent`, and `gemini-pro-agent` for reliable execution failover.
- **PyAutoGUI Screen Bounds Safety (`computer/operator.py`)**:
  - Refined mouse click and motion handlers to guarantee raw target coordinate execution while avoiding out-of-bounds PyAutoGUI failsafe crashes.
- **Unified Health Telemetry API (`server.py`)**:
  - Consolidated health metrics under `/health` and `/api/health` dual endpoint routing.
- **94-Test Verification Suite Integration (`tests/`)**:
  - Expanded test suite to cover Silero VAD, CDP DOM bridge, clipboard fallbacks, and step velocity evaluation.

---

## [37.30.0] — 2026-07-24

### Integrated Antigravity Agent Subsystem & Adaptive Step Architecture
- **Antigravity Scratchpad Engine (`agent/scratchpad.py` & `tools/scratchpad_tools.py`)**:
  - Isolated `./scratch/` execution workspace.
  - Multi-language transient script evaluator `scratchpad_eval` (Python, Node.js, PowerShell, Bash).
  - 5 registered scratchpad tools: `scratchpad_write`, `scratchpad_read`, `scratchpad_eval`, `scratchpad_list`, `scratchpad_clear`.
- **Autonomous Planning Mode & GFM Artifact Engine (`agent/planning_mode.py` & `agent/artifacts.py`)**:
  - Dynamic complexity classifier (`warrants_plan`) and automatic plan generation (`implementation_plan.md` & `walkthrough.md`).
  - GFM Artifact generator supporting alerts (`> [!IMPORTANT]`, `> [!NOTE]`), Mermaid diagrams, and `file:///` clickable links.
- **Trajectory Transcripts Logger (`agent/transcript_logger.py`)**:
  - Trajectory JSON Lines logger (`transcript.jsonl` & `transcript_full.jsonl`) integrated into ReAct chat loop.
- **Voice Prompt Refinement Engine (`voice/prompt_refiner.py`)**:
  - Acoustic speech cleaner, vocal filler stripper (`um`, `uh`, `like`, `you know`), domain vocabulary mapping via `config/vocabulary.json`, and transparent UI logging (`Spoken Raw` vs `Refined Prompt`).
- **Multi-Task & Sub-Agent Frontend Dashboard (`ui.py`)**:
  - Dedicated **"🚀 Multi-Tasks"** tab in Control Center rendering glossy **Task Cards**, progress bars, and status badges (`RUNNING`, `QUEUED`, `COMPLETED`, `FAILED`).
- **Conscious Step Planner & Adaptive Flexible Step Budget (`agent/step_planner.py` & `orchestrator.py`)**:
  - Goal decomposition into conscious sub-steps.
  - Replaced rigid step caps with `AdaptiveStepBudget` progress velocity evaluation, granting `+5` extensions (up to 60 steps max ceiling) when active tool progress is confirmed.
- **Multi-Backend Clipboard Utility (`actions/clipboard_utils.py`)**:
  - 5-layer prioritized fallback (`pyperclip` -> Win32 `ctypes` -> `tkinter` -> PowerShell -> CLI).
- **19-Test Automated Verification Suite (`tests/`)**:
  - 100% test pass rate across all new subsystems.

---

## [37.25.0] — 2026-07-23

### Critical Orchestrator Fix & Context Resolution Engine Upgrade
- **Critical Conversation Context Fix (`orchestrator.chat()`)**:
  - Resolved major conversation memory loss bug where the user message `augmented` string was constructed but never inserted into `WorkingMemory` prior to backend inference calls.
  - Re-established turn recording (`_record_turn("user", user_input)`) before starting the ReAct execution loop.

- **Context-Aware Pronoun & Browser Resolver (`orchestrator._resolve_context_references()`)**:
  - Implemented automatic anaphoric pronoun resolution for queries like `"open it in brave"`, `"open this in chrome"`, or `"show in edge"`.
  - Scans working memory history for recent output URLs (e.g. weather search URLs, RAG search URLs), directly launching the target browser (Brave, Chrome, Edge, Firefox) with the resolved URL.

- **Live OS Vision Target Trace Overlay (`actions/live_os_control.py`)**:
  - Implemented `_save_action_visualization()` drawing a red crosshair and target action footprint directly on target coordinates `(px_x, px_y)` for every executed step action.
  - Saves visual traces to `BR_WORKSPACE/Logs/live_os/step_{step}_action.png`.
  - Integrated dynamic `is_static` frame hash check to alert the vision model when click actions produce no screen change.

- **Zero-Token Intent Engine Expansion (Rounds 8–24)**:
  - Expanded `DeterministicIntentEngine` in `core/intent_engine.py` to 50+ instant 0-token matchers (Git branch, commit log, largest Python file, RAM free / garbage collection, battery, CPU frequency, disk partitions, swap memory, PATH environment, etc.).
  - Added `"brave"` and `"firefox"` to `APP_MAPPINGS` in `intent_engine.py` and `open_app.py`.

---

## [37.24.0] — 2026-07-23
### Added
- Round 24 voice upgrades: active Git branch 0-token intent trigger variants.

## [37.23.0] — 2026-07-23
### Added
- Round 23 voice upgrades: network IP and deep audit test trigger variations.

## [37.22.0] — 2026-07-23
### Added
- Round 22 voice upgrades: complex query, chaining, and timezone location guards in intent engine.

## [37.21.0] — 2026-07-23
### Added
- Round 21 voice upgrades: swap memory, CPU frequency, system PATH environment, and enhanced file discovery group intent matchers.

## [37.20.0] — 2026-07-23
### Added
- Round 20 voice upgrades: CPU Load, Python Modules count, and Disk Partitions telemetry intent matchers.

## [37.19.0] — 2026-07-23
### Upgraded
- Memory System Upgrade: added `add_user_message` and `add_assistant_message` helpers to `UnifiedMemoryManager`.

## [37.18.0] — 2026-07-23
### Added
- Round 18 voice upgrades: system timezone, markdown files counter, and largest Python source file scanner.

## [37.17.0] — 2026-07-23
### Added
- Round 17 voice upgrades: hostname, Python imports counter, and temp directory telemetry.

## [37.16.0] — 2026-07-23
### Added
- Round 16 voice upgrades: OS telemetry, Python classes counter, and settings app mappings.

## [37.15.0] — 2026-07-23
### Added
- Round 15 voice upgrades: network ping latency diagnostics and Python functions counter.

## [37.14.0] — 2026-07-23
### Added
- Round 14 voice upgrades: Git branch, installed Python packages, and clipboard inspection.

## [37.13.0] — 2026-07-23
### Added
- Round 13 voice upgrades: disk space, CPU info, active window, and deep audit test runner.

## [37.12.0] — 2026-07-23
### Added
- Round 12 voice upgrades: process count, virtualenv status, and environment variables.

## [37.11.0] — 2026-07-23
### Added
- Round 11 voice upgrades: display resolution, Python info, and recent commits intent matchers.

## [37.10.0] — 2026-07-23
### Added
- Round 10 voice upgrades: battery/power telemetry and workspace Git status.

## [37.9.0] — 2026-07-23
### Added
- Round 9 voice upgrades: system uptime and memory store summary.

## [37.8.0] — 2026-07-23
### Added
- Round 8 voice upgrades: lock screen, workspace health diagnostics, and project statistics.

## [37.7.0] — 2026-07-23
### Added
- Round 7 voice upgrades: Show Desktop, file discovery, and RAM flush.

---

## [37.6.0] — 2026-07-22

### Verified & Synchronized — Full Architecture Audit & System Alignment
- **Full Codebase Audit & Verification**:
  - Conducted complete repository audit across all 15 architectural subsystems (`core/`, `guardian/`, `evolution/`, `reasoning/`, `workflow/`, `agent/`, `multi_agent/`, `router.py`, `context/`, `memory/`, `computer/`, `vision/`, `voice/`, `tools/`, `events/`).
  - Fixed `ActionType` enum compatibility (`WINDOW_FOCUS`, `APP_FOCUS`) and control flow in `computer/operator.py`.
  - Fixed test mock frame inputs in `tests/test_vision_engine.py`.
  - Achieved **58/58 PASS (100% green)** in PyTest test suite and **42/42 PASS (100% green)** in Deep Audit test suite.

- **Architecture Knowledge Base Synchronization (`br_archetecture/`)**:
  - Updated `br_archetecture/full_repository_audit.md` with complete subsystem audit matrices and test metrics.
  - Updated `br_archetecture/README.md`, `br_archetecture/fullproject.md`, `br_archetecture/planning/FEATURE_MATRIX.md`, `br_archetecture/planning/TECHNICAL_DEBT.md`, and `br_archetecture/architecture/PROJECT_STRUCTURE.md`.

---

## [37.5.0] — 2026-07-21

### Added & Upgraded — Next-Gen Semantic Desktop & Hybrid Vision OS
- **Semantic UI Graph Engine (`vision/types.py`, `vision/engine.py`)**:
  - Implemented `UIRole` Enum (`BUTTON`, `TEXTBOX`, `DROPDOWN`, `DIALOG`, `TREE`, `EDITOR`, `BROWSER`, `WINDOW`, `ICON`, `TOOLBAR`, `SIDEBAR`, `TAB`, `TABLE`, etc.).
  - Implemented `SemanticUINode` tracking node ID, role, name, parent-child links, bounding box, states (`is_focused`, `is_enabled`, `is_clickable`), confidence, and source tier.
  - Implemented `SemanticUIGraph` hierarchy DAG with lookup APIs (`find_by_name`, `find_by_role`).

- **Tier 1 Accessibility API Bridge (`vision/accessibility.py`)**:
  - Implemented `AccessibilityBridge` extracting native OS control trees via Windows UI Automation `ctypes` in under 10ms with zero API token cost.

- **Tier 2 Browser DOM Bridge (`vision/dom_bridge.py`)**:
  - Implemented `CDPBridge` connecting to Chrome/Edge DevTools Protocol debugging port (`localhost:9222`) for web page DOM trees.

- **7-Tier Hybrid Vision Pipeline (`vision/hybrid_pipeline.py`)**:
  - Implemented `HybridVisionPipeline` combining Accessibility APIs, DOM trees, and fast local OCR into a unified `SemanticUIGraph`.

- **Vision Engine Telemetry (`vision/engine.py`)**:
  - Updated `VisionEngine` to run screen captures through the hybrid pipeline and publish `screen.understood` & `graph.updated` events onto `EventBus`.

- **Semantic Computer Operator (`computer/semantic_operator.py`)**:
  - Implemented `SemanticComputerOperator` accepting `SemanticTarget` component specifications and resolving dynamic coordinates at action time.

- **Self-Healing & Recovery Engine (`computer/recovery.py`)**:
  - Implemented `SelfHealingEngine` to intercept unexpected dialogs, auto-dismiss popups, reposition targets, and retry actions without failing master workflows.

- **Event System & Test Suite Upgrades (`events/types.py`, `tests/test_semantic_vision.py`)**:
  - Added `VisionEvent` taxonomy models.
  - Implemented `tests/test_semantic_vision.py` unit test suite (6/6 tests passing 100% green).
  - Total Test Coverage: **64/64 PASS** across Semantic Vision (6), Deep Audit (42), Integration (11), and Smoke (5).

---

## [37.4.0] — 2026-07-21

### Added & Upgraded
- **Reasoning Engine Subsystem (`reasoning/`)**:
  - Implemented `reasoning/types.py` data models (`TaskNode`, `PlanGraph`, `ConfidenceScore`, `ReasoningTrace`).
  - Implemented `reasoning/engine.py` master `ReasoningEngine` with Chain-of-Thought (CoT) ReAct expansion, risk confidence scoring, and self-verification trace checks.

- **Workflow Engine Subsystem (`workflow/`)**:
  - Implemented `workflow/dag.py` `WorkflowDAG` graph with dependency tracking and cycle detection.
  - Implemented `workflow/scheduler.py` background `TaskScheduler` supporting time/interval triggers.
  - Implemented `workflow/engine.py` durable `WorkflowEngine` managing state transitions (`PENDING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`) with SQLite state persistence (`workflows.db`).

- **Vision Engine Subsystem Upgrades (`vision/`)**:
  - Upgraded `vision/ocr_engine.py` with LRU caching, SHA-256 frame hash check, and PyTesseract bounding box extractions with clean fallback.
  - Upgraded `vision/screen_analyst.py` with multi-monitor selection (`get_monitors()`) and FNV-1a frame hashing.
  - Upgraded `vision/engine.py` with multi-monitor analysis and `vision.screen.analyzed` event publishing.

- **Computer Operator Subsystem Upgrades (`computer/`)**:
  - Upgraded `computer/operator.py` with PyAutoGUI mouse-corner security failsafes (`pyautogui.FAILSAFE = True`), async execution wrapper (`async_execute_action`), native win32 window focus matching, and action verification.

- **Voice Engine & Router Upgrades (`voice/`, `router.py`)**:
  - Upgraded `voice/stt.py` & `voice/whisper_local.py` for offline speech recognition.
  - Upgraded `voice/assistant.py` with wake-word gating and vocabulary correction.
  - Upgraded `router.py` adaptive complexity routing and token budgeting.

- **Backward Compatibility & Logging Resilience**:
  - Re-created 6 root backend compatibility shims (`anthropic_backend.py`, `gemini_backend.py`, `openai_backend.py`, `ollama_backend.py`, `nvidia_backend.py`, `mistral_backend.py`).
  - Fixed Windows standard stream logging encoding (`cp1252` `UnicodeEncodeError`) in `core/logging.py`.
  - Audited `actions/` modules to check `os.environ` (`GEMINI_API_KEY` / `GOOGLE_API_KEY`) before reading JSON configuration files.

- **Verification Results**:
  - 42/42 Deep Audit tests passing (`python test_deep_audit.py`).
  - 11/11 Integration tests passing (`python test_integration.py`).
  - 5/5 Startup Smoke checks passing (`python scripts/smoke_startup.py`).

---

## [37.3.0] — 2026-07-20

### Added
- **Subsystem 1: Core Runtime Engine (`core/`)**
  - Implemented `core/config.py` using Pydantic v2 `BaseSettings`.
  - Implemented `core/logging.py` with structured JSON & console formatting.
  - Implemented `core/di.py` for thread-safe Dependency Injection.
  - Implemented `core/lifecycle.py` for async startup & shutdown signal management.
  - Implemented `core/process.py` for background process supervision.
  - Implemented `core/health.py` for hardware metrics & service health checks.
  - Implemented `core/runtime.py` coordinator.
