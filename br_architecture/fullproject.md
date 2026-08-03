# 🌌 BR JARVIS — Master Architecture Record & Full Project Specification

> **System Identity**: BR JARVIS (Project BR / JARVIS MK38)
> **Version**: MK38.2.0 — Meta-Cognition, Speculative Core & World Intelligence Subsystems
> **Target Platform**: Windows 11 / Linux / macOS
> **Last Updated**: 2026-08-01
> **Test Coverage**: 110 automated Pytest unit & integration test suites passing cleanly (100% green)
> **File Inventory**: 350+ python & configuration source modules cataloged and audited

---

## 1. Executive Summary & Vision

**BR JARVIS** is a local-first, multi-modal cognitive AI operating system built for autonomous PC control, hands-free voice interaction, multi-backend LLM routing, screen vision, self-improvement, and immutable safety governance.

It is not a simple chatbot wrapper — it is a full **AI Operating System** with 18 specialized subsystems working together in an asynchronous, event-driven architecture.

### 🎯 Core Architectural Principles & Production Subsystems

| Principle / Subsystem | Primary Implementation Modules | Capabilities & Architectural Impact | Status |
|---|---|---|---|
| **Meta-Cognition Engine** | `reasoning/meta_cognition.py` | Pre-execution risk assessment, confidence scoring ($0.0 \text{ to } 1.0$), and safety gate validation | ✅ Production |
| **Speculative Execution Engine** | `reasoning/speculative.py`, `orchestrator/speculative.py` | Parallel speculative draft step generation & step validation | ✅ Production |
| **Trajectory Experience Replay DB** | `memory/experience_replay.py` | SQLite WAL trajectory store for similarity retrieval & step playback | ✅ Production |
| **Temporal Knowledge Graph 2.0** | `memory/temporal_kg.py` | Time-stamped relational edges $(e_1, r, e_2, t_{\text{start}}, t_{\text{end}})$ & `query_as_of` temporal snapshots | ✅ Production |
| **Semantic Workspace Code Graph** | `workspace/code_graph.py` | Zero-token AST code symbol definition & reference resolution | ✅ Production |
| **Closed-Loop Cognitive Cycle** | `reasoning/cognitive_loop.py`, `agent/critic_agent.py` | Observe -> Think -> Critic -> Improve -> Retry closed cognitive cycle | ✅ Production |
| **Relational Knowledge Graph World Model** | `memory/knowledge_graph.py` | NetworkX relational entity graph connecting workspace resources | ✅ Production |
| **Persistent Task DAG & Crash Resume** | `workflow/task_dag.py` | SQLite WAL atomic step checkpointing (`checkpoint()`, `resume()`) | ✅ Production |
| **Multi-Objective Model Router** | `router/core.py`, `router.py` | `select_multi_objective_backend()` balancing Quality, Cost, and Latency | ✅ Production |
| **Memory Decay & Forgetting Engine** | `memory/decay.py` | Ebbinghaus retention decay engine classifying memories into `RETAIN`, `ARCHIVE`, `PRUNE` | ✅ Production |
| **Ultra-Fast Silero VAD Voice Engine** | `voice/silero_vad.py` | ONNX Silero VAD segmenter for acoustic speech chunking (<10ms latency) | ✅ Production |
| **Zero-Disk Whisper Audio Streaming** | `voice/whisper_local.py` | In-memory audio byte streaming with RMS silence gating & hallucination filter | ✅ Production |
| **CDP DOM Bridge Vision Tier** | `vision/dom_bridge.py` | Real-time Chrome/Edge browser accessibility DOM inspection bridge | ✅ Production |
| **Zero-Token Instant Execution** | `core/intent_engine.py` | 50+ deterministic matchers executing system commands in 0ms, 0 LLM tokens | ✅ Production |
| **Voice Prompt Refinement Engine** | `voice/prompt_refiner.py` | Vocal hesitation cleaner, filler stripper (`um`, `uh`, `like`), and vocab mapper | ✅ Production |
| **Conscious Step Planner & Adaptive Budget** | `agent/step_planner.py` | Goal decomposition & progress velocity evaluator (+5 step extensions up to 60 ceiling) | ✅ Production |
| **Antigravity Scratchpad Engine** | `agent/scratchpad.py`, `tools/scratchpad_tools.py` | Isolated `./scratch/` workspace & multi-lang `scratchpad_eval` | ✅ Production |
| **Autonomous Planning Mode & GFM Artifacts** | `agent/planning_mode.py`, `agent/artifacts.py` | Dynamic complexity classifier, `implementation_plan.md` & `walkthrough.md` | ✅ Production |
| **Trajectory Transcripts Logging** | `agent/transcript_logger.py` | JSON Lines trajectory logger (`transcript.jsonl`) | ✅ Production |
| **Multi-Task & Sub-Agent UI Dashboard** | `ui.py`, `ui_mark.py` | Control Center tab displaying Task Cards with status badges (`RUNNING`, `QUEUED`, `COMPLETED`, `FAILED`), progress bars & canvas HUD | ✅ Production |
| **Multi-Backend Clipboard Engine** | `actions/clipboard_utils.py` | 5-layer prioritized fallback (`pyperclip` -> Win32 `ctypes` -> `tkinter` -> PowerShell -> CLI) | ✅ Production |
| **Context-Aware Pronoun Resolution** | `orchestrator/core.py` | Resolves contextual references ("open it in brave") using history window | ✅ Production |
| **Multi-Backend LLM Routing** | `router/core.py`, `backends/` | 7 backends: Gemini, Claude, GPT, DeepSeek, NVIDIA, Ollama, Mistral | ✅ Production |
| **Immutable Guardian Core** | `guardian/core.py`, `guardian/kill_switch.py` | Kill-switch, snapshot, rollback, SHA256 audit ledger | ✅ Production |
| **Autonomous Self-Upgrade** | `evolution/` | Blast-radius classifier, sandbox testing, auto-deploy | ✅ Production |
| **Multi-Tier Memory** | `memory/unified_memory.py` | 5 storage tiers: Working, SQLite, ChromaDB, LessonStore, FNV-1a cache | ✅ Production |
| **Live OS Vision Control** | `actions/live_os_control.py` | Screenshot -> LLM -> Action loop with visual grounding trace | ✅ Production |
| **Deep Desktop Automation** | `computer/operator.py` | Win32, PyAutoGUI, accessibility trees | ✅ Production |
| **7-Tier Vision Pipeline** | `vision/engine.py` | Screen capture, OCR, DOM bridge, accessibility, hybrid pipeline | ✅ Production |

---

## 2. System Architecture Topology

```mermaid
graph TD
    User([👤 User Voice / Text / API]) --> VoiceRefiner[VoicePromptRefiner<br/>voice/prompt_refiner.py]
    VoiceRefiner --> Interface

    subgraph Interface["🖥️ Interface Layer"]
        VoiceUI[Voice GUI<br/>floating_voice_ui.py]
        TKUI[Tkinter Desktop UI<br/>ui.py, ui_mark.py & Multi-Task Dashboard]
        WebUI[Glassmorphic Web Dashboard<br/>web/ + server.py WebSocket]
        CLIUI[CLI REPL Orchestrator<br/>main_mk37.py]
    end

    Interface --> IntentEngine

    subgraph ZeroToken["⚡ Zero-Token Fast Path (0ms, 0 LLM tokens)"]
        IntentEngine[DeterministicIntentEngine<br/>core/intent_engine.py<br/>50+ instant matchers]
    end

    IntentEngine --> |Intercepted| Speaker[TTS Response<br/>voice/tts.py Edge-TTS / pyttsx3]
    IntentEngine --> |Needs LLM| StepPlanner

    subgraph PlanningAndBudget["🧠 Conscious Step Planner & Adaptive Budget"]
        StepPlanner[StepPlanner<br/>agent/step_planner.py]
        StepPlanner --> StepBudget[AdaptiveStepBudget<br/>Dynamic 5-35 steps + Progress Extensions]
        StepPlanner --> PlanningEngine[PlanningEngine<br/>agent/planning_mode.py]
    end

    subgraph Orchestrator["🧠 JarvisOrchestrator<br/>orchestrator/core.py"]
        StepBudget --> ContextResolver[Context Resolver<br/>context/engine.py]
        ContextResolver --> WorkingMemory[Working Memory<br/>memory/working.py]
        WorkingMemory --> ReactLoop[ReAct Loop<br/>Adaptive Step Budget]
    end

    ReActLoop --> ModelRouter[AgentRouter<br/>router/core.py]

    subgraph LLMBackends["🔀 Multi-LLM Provider Engine"]
        ModelRouter --> Gemini[Gemini 2.5 / 3.5 / Flash]
        ModelRouter --> Claude[Claude 3.5 Sonnet]
        ModelRouter --> GPT[GPT-4o / OSS 120B]
        ModelRouter --> DeepSeek[DeepSeek R1]
        ModelRouter --> NVIDIA[NVIDIA NIM Llama3]
        ModelRouter --> Ollama[Local Ollama]
    end

    subgraph ExecutionSubsystems["🔧 Subsystems & Tool Ecosystem"]
        ReActLoop --> ToolRegistry[Tool Registry<br/>tools/registry.py<br/>98+ Tools]
        ToolRegistry --> Scratchpad[Scratchpad Engine<br/>agent/scratchpad.py<br/>./scratch/ Workspace]
        ToolRegistry --> LiveOS[Live OS Controller<br/>actions/live_os_control.py]
        ToolRegistry --> CompOp[Computer Operator<br/>computer/operator.py]
        ToolRegistry --> Vision[Vision Engine<br/>vision/engine.py]
        ToolRegistry --> Memory[Multi-Tier Memory<br/>SQLite + ChromaDB + Temporal KG]
    end
```

---

## 3. Package & Module Directory Topology

### 3.1 Subsystem: `actions/`
**Description**: Granular Desktop, App, System, RAG, Reminders, Video & 5-Layer Clipboard Actions
**Total Modules**: 53

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/actions/__init__.py) | `5` | — | — | Action modules: browser control, file management, desktop automation, and more. |
| [app_analyzer.py](file:///d:\BRJARVIS\Br-Jarvis/actions/app_analyzer.py) | `300` | `SystemAppAnalyzer` | `get_app_analyzer()` | System Application Analyzer for BR-Jarvis. Scans installed applications across OS platforms (Windows, Linux, macOS) and  |
| [app_tracker.py](file:///d:\BRJARVIS\Br-Jarvis/actions/app_tracker.py) | `215` | `AppStartTracker` | `_get_db_path()`, `get_app_tracker()`, `log_app_launch()` | Application Launch Tracker & Persistent SQLite Storage for BR-Jarvis. Records application start events, tracks applicati |
| [automation_engine.py](file:///d:\BRJARVIS\Br-Jarvis/actions/automation_engine.py) | `202` | `UniversalAutomationEngine` | `get_automation_engine()` | Universal Automation Engine for BR-Jarvis. Enables application lifecycle control, mouse/keyboard macro automation, syste |
| [background_monitor.py](file:///d:\BRJARVIS\Br-Jarvis/actions/background_monitor.py) | `159` | — | `_is_blocked()`, `_slug()`, `_title_hash()` | BackgroundMonitor — user-configured topic watching. Checks DDG news once per day per topic; alerts JARVIS when a new hea |
| [browser_control.py](file:///d:\BRJARVIS\Br-Jarvis/actions/browser_control.py) | `1060` | `_BrowserSession`, `_SessionRegistry` | `_normalize_url()`, `_user_agent()`, `_real_profile_dir()` | Core subsystem module |
| [calendar_engine.py](file:///d:\BRJARVIS\Br-Jarvis/actions/calendar_engine.py) | `291` | `CalendarEngine` | `_get_db_path()`, `get_calendar_engine()` | Mobile Gemini-Style Calendar & Task Engine for BR-Jarvis. Manages tasks and calendar events with natural language dateti |
| [chat_export.py](file:///d:\BRJARVIS\Br-Jarvis/actions/chat_export.py) | `210` | — | `_output_dir()`, `export_chat()`, `_export_md()` | Exports conversation history to multiple formats: PDF, Markdown, HTML, Plain Text. |
| [cli_controller.py](file:///d:\BRJARVIS\Br-Jarvis/actions/cli_controller.py) | `445` | `ShellSession` | `_detect_shell()`, `_get_main_session()`, `_get_named_session()` | BR Voice Assistant — CLI Controller (actions/cli_controller.py) Windows-specialized terminal command execution. Optimize |
| [clipboard_history.py](file:///d:\BRJARVIS\Br-Jarvis/actions/clipboard_history.py) | `146` | `ClipboardTracker` | `tool_clipboard_history()` | Background clipboard history monitor for JARVIS MK37. Logs clipboard copies to a SQLite database and provides search too |
| [clipboard_utils.py](file:///d:\BRJARVIS\Br-Jarvis/actions/clipboard_utils.py) | `222` | — | `get_clipboard_text()`, `set_clipboard_text()` | Robust, multi-backend system clipboard interface for BR JARVIS. Provides fallbacks across pyperclip, Win32 API, Tkinter, |
| [code_helper.py](file:///d:\BRJARVIS\Br-Jarvis/actions/code_helper.py) | `584` | — | `get_base_dir()`, `_get_api_key()`, `_get_gemini()` | Core subsystem module |
| [computer_control.py](file:///d:\BRJARVIS\Br-Jarvis/actions/computer_control.py) | `560` | — | `_base_dir()`, `_load_config()`, `_platform_os()` | Core subsystem module |
| [computer_settings.py](file:///d:\BRJARVIS\Br-Jarvis/actions/computer_settings.py) | `717` | — | `_get_base_dir()`, `_get_api_key()`, `_get_macos_wifi_interface()` | Core subsystem module |
| [custom_commands.py](file:///d:\BRJARVIS\Br-Jarvis/actions/custom_commands.py) | `182` | `CustomCommandEngine` | — | User-defined custom commands, aliases, replies, and variables. Allows users to automate chains of actions (speak, open u |
| [desktop.py](file:///d:\BRJARVIS\Br-Jarvis/actions/desktop.py) | `501` | — | `_get_base_dir()`, `_get_api_key()`, `_get_desktop()` | Core subsystem module |
| [dev_agent.py](file:///d:\BRJARVIS\Br-Jarvis/actions/dev_agent.py) | `602` | `RateLimitError` | `get_base_dir()`, `_get_api_key()`, `_get_model()` | Core subsystem module |
| [email_assistant.py](file:///d:\BRJARVIS\Br-Jarvis/actions/email_assistant.py) | `132` | — | `_sync_auth()`, `_send_email()`, `_fetch_emails()` | Email utility assistant for JARVIS MK37. Supports sending (SMTP), checking (IMAP), and summarizing emails. |
| [fast_file_search.py](file:///d:\BRJARVIS\Br-Jarvis/actions/fast_file_search.py) | `100` | — | `search_files_by_name()`, `search_file_contents()`, `fast_file_search_action()` | Pika Voice-style Advanced Desktop File Search engine. Searches files by name, extension, or inside text contents across  |
| [file_controller.py](file:///d:\BRJARVIS\Br-Jarvis/actions/file_controller.py) | `543` | — | `_is_safe_path()`, `_get_desktop()`, `_get_downloads()` | Core subsystem module |
| [file_importer.py](file:///d:\BRJARVIS\Br-Jarvis/actions/file_importer.py) | `113` | — | `get_base_dir()`, `import_file_to_knowledge()` | Multi-File Knowledge Importer Engine for BR JARVIS. Ingests files (.txt, .pdf, .docx, .md, .csv, .xlsx, .vcf, .json) int |
| [file_processor.py](file:///d:\BRJARVIS\Br-Jarvis/actions/file_processor.py) | `838` | — | `_get_api_key()`, `_gemini_client()`, `_detect_type()` | file_processor.py — JARVIS Universal File Processor  Supported types:   image   → describe, ocr, resize, convert, compre |
| [flight_finder.py](file:///d:\BRJARVIS\Br-Jarvis/actions/flight_finder.py) | `364` | — | `_get_base_dir()`, `_get_api_key()`, `_parse_date()` | Core subsystem module |
| [galaxy.py](file:///d:\BRJARVIS\Br-Jarvis/actions/galaxy.py) | `139` | — | `ensure_dirs()`, `build_galaxy_graph()`, `query_galaxy()` | Scans markdown notes and long-term memory to build 3D force graph data (graph-data.js). Supports node search, camera fly |
| [game_updater.py](file:///d:\BRJARVIS\Br-Jarvis/actions/game_updater.py) | `1054` | — | `_find_steam_path()`, `_find_steam_windows()`, `_find_steam_mac()` | Core subsystem module |
| [gmail_auth.py](file:///d:\BRJARVIS\Br-Jarvis/actions/gmail_auth.py) | `165` | `GmailAuthManager` | `_get_config_dir()`, `get_gmail_auth_manager()` | Gmail Login & Authentication Manager for BR-Jarvis. Supports interactive browser login to Google/Gmail, App Password con |
| [hotkeys.py](file:///d:\BRJARVIS\Br-Jarvis/actions/hotkeys.py) | `129` | `HotkeyManager` | — | Registers global keyboard shortcuts using the 'keyboard' module. Allows users to trigger actions like toggling voice lis |
| [image_generator.py](file:///d:\BRJARVIS\Br-Jarvis/actions/image_generator.py) | `244` | — | `_output_dir()`, `_make_filename()`, `generate_image()` | AI image generation using multiple providers:   - Gemini Imagen (primary, via google.genai SDK)   - OpenAI DALL-E 3 (via |
| [live_os_control.py](file:///d:\BRJARVIS\Br-Jarvis/actions/live_os_control.py) | `902` | `LiveOSController` | `_base_dir()`, `_draw_grid_overlay()`, `_save_action_visualization()` | Live Autonomous OS Visual Control Engine ("Antigravity Live Control"). Real-time screen perception, visual grounding, fa |
| [longform_builder.py](file:///d:\BRJARVIS\Br-Jarvis/actions/longform_builder.py) | `240` | — | `_sanitize_folder_name()`, `build_longform_publication()`, `longform_builder_action()` | BR-JARVIS Master Long-Form Book & Project Builder. Generates comprehensive multi-chapter books, technical manuals, archi |
| [open_app.py](file:///d:\BRJARVIS\Br-Jarvis/actions/open_app.py) | `289` | — | `_normalize()`, `_launch_windows()`, `_launch_macos()` | Core subsystem module |
| [proactive.py](file:///d:\BRJARVIS\Br-Jarvis/actions/proactive.py) | `124` | `ProactiveEngine` | — | ProactiveEngine 2.0 — context-aware, time-aware, non-repetitive background prompting. Gemini decides what to say; this m |
| [process_optimizer.py](file:///d:\BRJARVIS\Br-Jarvis/actions/process_optimizer.py) | `65` | `ProcessOptimizerAction` | `run_process_optimization()` | Autonomous action for process priority management, identifying memory hogs, and terminating unresponsive background task |
| [rag_library.py](file:///d:\BRJARVIS\Br-Jarvis/actions/rag_library.py) | `650` | — | `_get_collection()`, `_extract_text_pdf()`, `_extract_text_docx()` | Retrieval-Augmented Generation (RAG) for chatting with personal documents. Supports: PDF, DOCX, TXT, CSV, Markdown, webp |
| [reminder.py](file:///d:\BRJARVIS\Br-Jarvis/actions/reminder.py) | `337` | — | `_base_dir()`, `_get_os()`, `_scripts_dir()` | Core subsystem module |
| [reminders.py](file:///d:\BRJARVIS\Br-Jarvis/actions/reminders.py) | `182` | `ReminderManager` | `get_reminder_manager()`, `reminder_tool_action()` | Pika Voice-style Smart Reminder Engine. Schedules one-time or recurring reminders, tracks active tasks, and triggers nat |
| [repo_controller.py](file:///d:\BRJARVIS\Br-Jarvis/actions/repo_controller.py) | `60` | `RepoControllerAction` | `inspect_repository()` | Autonomous action controller for git repository workflows, diff inspection, branch management, and automated commit oper |
| [scheduler.py](file:///d:\BRJARVIS\Br-Jarvis/actions/scheduler.py) | `230` | `TaskScheduler` | `tool_scheduler()` | Natural language task scheduler for JARVIS MK37. Allows scheduling goals (e.g. "every day at 9:00am") and running them v |
| [screen_processor.py](file:///d:\BRJARVIS\Br-Jarvis/actions/screen_processor.py) | `464` | `_VisionSession` | `_base_dir()`, `_load_config()`, `_save_config_key()` | Core subsystem module |
| [screen_share.py](file:///d:\BRJARVIS\Br-Jarvis/actions/screen_share.py) | `369` | `ScreenShareServer` | `list_monitors()`, `_capture_frame_mss()`, `_capture_frame_pag()` | JARVIS MK37 — Enhanced Screen Share (actions/screen_share.py v2.0)  Improvements:   - Adaptive FPS throttling (drops fra |
| [send_message.py](file:///d:\BRJARVIS\Br-Jarvis/actions/send_message.py) | `266` | — | `_base_dir()`, `_get_os()`, `_require_pyautogui()` | Core subsystem module |
| [smart_email_sender.py](file:///d:\BRJARVIS\Br-Jarvis/actions/smart_email_sender.py) | `275` | `SmartEmailSender` | `_get_contacts_file()`, `_get_scheduled_file()`, `get_smart_email_sender()` | Smart Email Creation & Automated Sending Engine for BR-Jarvis. Supports sending emails to any recipient or saved contact |
| [sqlite_manager.py](file:///d:\BRJARVIS\Br-Jarvis/actions/sqlite_manager.py) | `73` | `SQLiteManagerAction` | — | Autonomous action for SQLite database schema inspection, vacuum optimization, table stats, and backup creation. |
| [system_cleanup.py](file:///d:\BRJARVIS\Br-Jarvis/actions/system_cleanup.py) | `73` | `SystemCleanupAction` | `execute_system_cleanup()` | Autonomous action to scan and clean temporary system files, obsolete log files, build artifacts, and free up disk space. |
| [system_monitor.py](file:///d:\BRJARVIS\Br-Jarvis/actions/system_monitor.py) | `200` | `SystemMonitor` | `_nvml_gpu()`, `_get_gpu_usage()`, `_get_cpu_temp()` | System Monitor — background metric checks with voice alert support. Zero subprocess calls on all platforms — uses ctypes |
| [system_optimizer.py](file:///d:\BRJARVIS\Br-Jarvis/actions/system_optimizer.py) | `75` | — | `optimize_system_resources()`, `system_optimizer_action()` | JARVIS Autonomous System & Memory Optimization Action. Cleans temporary cache files, collects garbage, inspects RAM usag |
| [transcriber.py](file:///d:\BRJARVIS\Br-Jarvis/actions/transcriber.py) | `69` | — | `transcribe_file()`, `transcribe_batch()`, `supported_formats()` | Offline audio and video file transcription using local Whisper. Supports: MP3, WAV, M4A, OGG, FLAC, MP4, MKV, AVI, WEBM. |
| [video_generator.py](file:///d:\BRJARVIS\Br-Jarvis/actions/video_generator.py) | `201` | — | `_output_dir()`, `_make_filename()`, `generate_video()` | AI video generation using multiple providers:   - Google Veo (primary, via google.genai SDK)   - Kling (via REST API, if |
| [weather_report.py](file:///d:\BRJARVIS\Br-Jarvis/actions/weather_report.py) | `51` | — | `weather_action()`, `_log()` | Core subsystem module |
| [web_app_controller.py](file:///d:\BRJARVIS\Br-Jarvis/actions/web_app_controller.py) | `99` | — | — | High-level automated workflows for online web apps (Gmail & Microsoft 365). |
| [web_search.py](file:///d:\BRJARVIS\Br-Jarvis/actions/web_search.py) | `308` | — | `_get_base_dir()`, `_get_api_key()`, `_gemini_search()` | Core subsystem module |
| [whatsapp_automation.py](file:///d:\BRJARVIS\Br-Jarvis/actions/whatsapp_automation.py) | `257` | `WhatsAppAutomation` | `_get_contacts_file()`, `_get_scheduled_messages_file()`, `get_whatsapp_automation()` | WhatsApp Automation Engine for BR-Jarvis. Supports direct messaging to any contact or phone number via WhatsApp URI & We |
| [youtube_video.py](file:///d:\BRJARVIS\Br-Jarvis/actions/youtube_video.py) | `437` | — | `_get_base_dir()`, `_get_api_key()`, `_open_url()` | Core subsystem module |

### 3.2 Subsystem: `agent/`
**Description**: Cognitive Agent Engine, ReAct Planner, Execution Pipeline, Scratchpad, Task Scheduler & Planning Mode
**Total Modules**: 15

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/agent/__init__.py) | `18` | — | — | Core subsystem module |
| [artifacts.py](file:///d:\BRJARVIS\Br-Jarvis/agent/artifacts.py) | `88` | `ArtifactMetadata`, `ArtifactDocument` | `make_file_link()` | Artifact Document Generator for BR JARVIS. Renders GitHub-Flavored Markdown documents with alerts (> [!NOTE]), mermaid d |
| [critic_agent.py](file:///d:\BRJARVIS\Br-Jarvis/agent/critic_agent.py) | `91` | `CritiqueResult`, `CriticAgent` | — | Dedicated CriticAgent that reviews execution plans, step outputs, and tool responses to prevent hallucinated completions |
| [error_handler.py](file:///d:\BRJARVIS\Br-Jarvis/agent/error_handler.py) | `225` | `ErrorDecision` | `get_base_dir()`, `_get_api_key()`, `analyze_error()` | Core subsystem module |
| [executor.py](file:///d:\BRJARVIS\Br-Jarvis/agent/executor.py) | `424` | `StepResult`, `AgentExecutor`, `ParallelGoalExecutor` | `_call_tool()` | High-performance task executor with TRUE parallel execution. - Runs independent steps simultaneously in a thread pool -  |
| [executor_engine.py](file:///d:\BRJARVIS\Br-Jarvis/agent/executor_engine.py) | `172` | `ParallelExecutionEngine` | `get_executor_engine()` | Core subsystem module |
| [planner.py](file:///d:\BRJARVIS\Br-Jarvis/agent/planner.py) | `200` | — | `_get_gemini()`, `create_plan()`, `replan()` | AI-powered task planner using Gemini. Creates structured plans with dependency tracking and parallel execution support. |
| [planner_engine.py](file:///d:\BRJARVIS\Br-Jarvis/agent/planner_engine.py) | `168` | `PlannerEngine` | `get_planner_engine()` | Core subsystem module |
| [planning_mode.py](file:///d:\BRJARVIS\Br-Jarvis/agent/planning_mode.py) | `163` | `PlanningEngine` | `_get_planning_dir()`, `get_planning_engine()` | Planning Mode Engine for BR JARVIS. Evaluates goal complexity, generates implementation_plan.md and walkthrough.md, and  |
| [scratchpad.py](file:///d:\BRJARVIS\Br-Jarvis/agent/scratchpad.py) | `171` | `ScratchpadManager` | `_get_scratch_dir()`, `get_scratchpad()` | Scratchpad Engine for BR JARVIS. Provides temporary workspace script execution, scratch memory context, and transient da |
| [step_planner.py](file:///d:\BRJARVIS\Br-Jarvis/agent/step_planner.py) | `112` | `AdaptiveStepBudget`, `StepPlanner` | — | Conscious Step Planner & Adaptive Flexible Step Budget Engine for BR JARVIS. Dynamically plans execution sub-steps and c |
| [task_queue.py](file:///d:\BRJARVIS\Br-Jarvis/agent/task_queue.py) | `305` | `TaskStatus`, `TaskPriority`, `Task`, `TaskQueue` | `get_queue()` | High-performance task queue with parallel execution support. - Concurrent goal execution (multiple tasks at once) - Prio |
| [task_scheduler.py](file:///d:\BRJARVIS\Br-Jarvis/agent/task_scheduler.py) | `69` | `TaskScheduler` | — | TaskScheduler manages asynchronous DAG task queues and worker dispatches, decoupling goal planning from orchestrator exe |
| [transcript_logger.py](file:///d:\BRJARVIS\Br-Jarvis/agent/transcript_logger.py) | `84` | `TranscriptLogger` | `_get_log_dir()`, `get_transcript_logger()` | Transcript Trajectory Logger for BR JARVIS. Logs chronological step execution, tool calls, model thoughts, and sub-agent |
| [types.py](file:///d:\BRJARVIS\Br-Jarvis/agent/types.py) | `61` | `RiskLevel`, `StepStatus`, `TaskStepNode`, `GoalGraph`, `ExecutionReport` | — | Core subsystem module |

### 3.3 Subsystem: `backends/`
**Description**: AI Provider LLM Adapters (Gemini, Claude, OpenAI, DeepSeek, NVIDIA, Ollama, Mistral)
**Total Modules**: 9

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/backends/__init__.py) | `52` | — | — | Unified AI backend package. Auto-discovers and exports all backend classes. All optional backends are guarded with try/e |
| [anthropic.py](file:///d:\BRJARVIS\Br-Jarvis/backends/anthropic.py) | `109` | `ClaudeBackend` | — | Anthropic (Claude) backend connector for BR Core. Safe initialization, standardized error handling, and text streaming. |
| [base.py](file:///d:\BRJARVIS\Br-Jarvis/backends/base.py) | `81` | `BaseBackend` | — | Abstract base class that ALL AI backends must implement. Provides a consistent interface for completion, streaming, and  |
| [deepseek.py](file:///d:\BRJARVIS\Br-Jarvis/backends/deepseek.py) | `86` | `DeepSeekBackend` | — | DeepSeek and OpenRouter backend connector for BR Core. Supports DeepSeek-R1 reasoning models, DeepSeek-V3, and OpenRoute |
| [gemini.py](file:///d:\BRJARVIS\Br-Jarvis/backends/gemini.py) | `445` | `GeminiBackend` | — | Robust Gemini backend — the ONLY required backend for JARVIS MK37. Supports: text completion, streaming, vision, groundi |
| [mistral.py](file:///d:\BRJARVIS\Br-Jarvis/backends/mistral.py) | `93` | `MistralBackend` | — | Mistral backend connector for BR Core. Uses the OpenAI SDK pointed at Mistral's API endpoint. |
| [nvidia.py](file:///d:\BRJARVIS\Br-Jarvis/backends/nvidia.py) | `114` | `NvidiaBackend` | — | NVIDIA NIM backend connector for BR Core. Uses the OpenAI SDK pointed at NVIDIA's API endpoint. |
| [ollama.py](file:///d:\BRJARVIS\Br-Jarvis/backends/ollama.py) | `97` | `OllamaBackend` | — | Ollama backend for local/private inference. Safe initialization, standardized error handling, and text streaming. |
| [openai_compat.py](file:///d:\BRJARVIS\Br-Jarvis/backends/openai_compat.py) | `193` | `OpenAIBackend` | — | OpenAI (GPT) backend connector for BR Core. Supports custom base_url for local proxies (e.g., localhost:8045). |

### 3.4 Subsystem: `computer/`
**Description**: PC Operator, Semantic Finder, Desktop Automation & Recovery Subsystem
**Total Modules**: 5

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/computer/__init__.py) | `13` | — | — | Core subsystem module |
| [operator.py](file:///d:\BRJARVIS\Br-Jarvis/computer/operator.py) | `282` | `ComputerOperator` | `get_computer_operator()` | Core subsystem module |
| [recovery.py](file:///d:\BRJARVIS\Br-Jarvis/computer/recovery.py) | `117` | `SelfHealingEngine` | `get_self_healing_engine()` | Core subsystem module |
| [semantic_operator.py](file:///d:\BRJARVIS\Br-Jarvis/computer/semantic_operator.py) | `119` | `SemanticTarget`, `SemanticComputerOperator` | `get_semantic_operator()` | Core subsystem module |
| [types.py](file:///d:\BRJARVIS\Br-Jarvis/computer/types.py) | `47` | `ActionType`, `ComputerAction`, `ActionResult` | — | Core subsystem module |

### 3.5 Subsystem: `config/`
**Description**: Model Architecture Configuration, Hotkeys & Complexity Router Rules
**Total Modules**: 4

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/config/__init__.py) | `42` | — | `get_config()`, `get_gemini_api_key()`, `get_os()` | Core subsystem module |
| [complexity_router.py](file:///d:\BRJARVIS\Br-Jarvis/config/complexity_router.py) | `356` | `TaskComplexity`, `ComplexityAnalyzer` | `calculate_complexity_score()`, `analyze_complexity()`, `select_model_for_prompt()` | Advanced Semantic & Structural Complexity Analyzer. Calculates a weighted complexity score S in [0, 100] based on 6 anal |
| [model_loader.py](file:///d:\BRJARVIS\Br-Jarvis/config/model_loader.py) | `68` | — | `load_models()`, `save_models()` | Central model configuration loader for JARVIS MK37. Reads config/models.json and provides defaults if it doesn't exist. |
| [models.py](file:///d:\BRJARVIS\Br-Jarvis/config/models.py) | `149` | — | `get_model_config()`, `clear_model_config_cache()`, `get_model()` | Central model configuration. Gemini is the primary backend. Priority: ENV VARS > models.json > hardcoded defaults |

### 3.6 Subsystem: `context/`
**Description**: Token Manager, Dynamic Context Window Compressor & Reference Resolver
**Total Modules**: 7

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/context/__init__.py) | `20` | — | — | Core subsystem module |
| [builder.py](file:///d:\BRJARVIS\Br-Jarvis/context/builder.py) | `115` | `ContextBuilder` | — | Core subsystem module |
| [compressor.py](file:///d:\BRJARVIS\Br-Jarvis/context/compressor.py) | `51` | `ContextCompressor` | — | Core subsystem module |
| [engine.py](file:///d:\BRJARVIS\Br-Jarvis/context/engine.py) | `99` | `ContextEngine` | `get_context_engine()` | Core subsystem module |
| [token_counter.py](file:///d:\BRJARVIS\Br-Jarvis/context/token_counter.py) | `58` | `TokenCounter` | — | Core subsystem module |
| [token_manager.py](file:///d:\BRJARVIS\Br-Jarvis/context/token_manager.py) | `83` | `TokenBudgetManager`, `ContextTokenTrimmer` | — | Token Budget Manager & Sliding Window History Trimmer. Monitors token usage, enforces context window caps (default 12,00 |
| [types.py](file:///d:\BRJARVIS\Br-Jarvis/context/types.py) | `60` | `ContextScope`, `ContextItem`, `TokenBudget`, `AssembledContext` | — | Core subsystem module |

### 3.7 Subsystem: `core/`
**Description**: Micro-Kernel Bootstrap, DI Container, Zero-Token Intent Engine, Error Middleware & Health Monitor
**Total Modules**: 20

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/core/__init__.py) | `5` | — | — | Core subsystem package: bootstrap, config, DI, runtime, intent engine, and utilities. |
| [bootstrap.py](file:///d:\BRJARVIS\Br-Jarvis/core/bootstrap.py) | `68` | `AssistantRuntime` | `build_assistant_runtime()` | Core subsystem module |
| [bootstrapper.py](file:///d:\BRJARVIS\Br-Jarvis/core/bootstrapper.py) | `91` | `CoreBootstrapper` | — | Unified System Bootstrapper for BR JARVIS. Standardizes environment initialization, encoding setup, API key validation,  |
| [compat.py](file:///d:\BRJARVIS\Br-Jarvis/core/compat.py) | `202` | — | — | Backward-compatible shim layer for JARVIS MK37.  Re-exports any renamed or moved symbols so existing skills/, agents/, a |
| [config.py](file:///d:\BRJARVIS\Br-Jarvis/core/config.py) | `100` | `AssistantConfig`, `ModelConfig`, `SystemConfig`, `HardwareConfig`, `JarvisConfig` | `get_config()` | Core subsystem module |
| [di.py](file:///d:\BRJARVIS\Br-Jarvis/core/di.py) | `77` | `Container` | `get_container()` | Core subsystem module |
| [error_middleware.py](file:///d:\BRJARVIS\Br-Jarvis/core/error_middleware.py) | `53` | `ErrorMiddleware` | `get_error_middleware()` | Core subsystem module |
| [health.py](file:///d:\BRJARVIS\Br-Jarvis/core/health.py) | `120` | `HardwareMetrics`, `ComponentHealth`, `HealthReport`, `HealthMonitor` | — | Core subsystem module |
| [installer.py](file:///d:\BRJARVIS\Br-Jarvis/core/installer.py) | `138` | — | `_available()`, `_pip()`, `install_for_config()` | MARK XL — Dependency auto-installer.  Called automatically on first launch and after engine reconfiguration. Installs on |
| [integration.py](file:///d:\BRJARVIS\Br-Jarvis/core/integration.py) | `54` | `IntegrationBridge` | `get_integration_bridge()` | Core subsystem module |
| [intent_engine.py](file:///d:\BRJARVIS\Br-Jarvis/core/intent_engine.py) | `1750` | `DeterministicIntentEngine` | — | Zero-LLM Fast Action Router. Parses standard user intentions (launching apps, opening websites, controlling audio/system |
| [lifecycle.py](file:///d:\BRJARVIS\Br-Jarvis/core/lifecycle.py) | `92` | `SystemState`, `LifecycleManager` | — | Core subsystem module |
| [logging.py](file:///d:\BRJARVIS\Br-Jarvis/core/logging.py) | `124` | `JSONFormatter`, `ColoredConsoleFormatter`, `LogTimer` | `setup_logger()` | Core subsystem module |
| [native_bridge.py](file:///d:\BRJARVIS\Br-Jarvis/core/native_bridge.py) | `194` | — | `_init_native()`, `is_native_active()`, `get_status()` | High-performance C/C++ native bridge for JARVIS MK37. Provides fast FNV-1a hashing, C-level audio VAD energy calculation |
| [personality.py](file:///d:\BRJARVIS\Br-Jarvis/core/personality.py) | `36` | — | `get_boot_briefing()` | Provides prompt conditioning for JARVIS's classic, warm, highly intelligent AI Assistant persona. |
| [process.py](file:///d:\BRJARVIS\Br-Jarvis/core/process.py) | `81` | `TaskStatus`, `ProcessSupervisor` | — | Core subsystem module |
| [retry.py](file:///d:\BRJARVIS\Br-Jarvis/core/retry.py) | `91` | — | `retry()` | Provides a configurable retry decorator with exponential backoff for external API calls, tool executions, and network op |
| [runtime.py](file:///d:\BRJARVIS\Br-Jarvis/core/runtime.py) | `55` | `CoreRuntime` | `get_runtime()` | Core subsystem module |
| [timeouts.py](file:///d:\BRJARVIS\Br-Jarvis/core/timeouts.py) | `24` | `TimeoutConfig` | `get_timeout_config()` | Core subsystem module |
| [workspace_engine.py](file:///d:\BRJARVIS\Br-Jarvis/core/workspace_engine.py) | `178` | `CognitiveWorkspaceEngine` | `_get_project_root()` | Core Cognitive Workspace Engine for BR JARVIS AI OS. Manages BR_WORKSPACE/ root vault, project lifecycles, self-healing  |

### 3.8 Subsystem: `dashboard/`
**Description**: FastAPI Management Dashboard Server
**Total Modules**: 2

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/dashboard/__init__.py) | `0` | — | — | Core subsystem module |
| [server.py](file:///d:\BRJARVIS\Br-Jarvis/dashboard/server.py) | `796` | `DashboardServer` | `_make_uploads_dir()`, `_get_gemini_key()`, `_derive_key()` | dashboard/server.py — JARVIS Local HTTP Dashboard  Plain HTTP on port 8000 (no SSL warnings, no firewall issues). Securi |

### 3.9 Subsystem: `events/`
**Description**: Asynchronous Pub/Sub EventBus, Event Types, Store & System Topics
**Total Modules**: 5

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/events/__init__.py) | `29` | — | — | Core subsystem module |
| [bus.py](file:///d:\BRJARVIS\Br-Jarvis/events/bus.py) | `123` | `EventBus` | `get_event_bus()` | Core subsystem module |
| [handlers.py](file:///d:\BRJARVIS\Br-Jarvis/events/handlers.py) | `20` | — | `subscribe()` | Core subsystem module |
| [store.py](file:///d:\BRJARVIS\Br-Jarvis/events/store.py) | `56` | `EventStore` | — | Core subsystem module |
| [types.py](file:///d:\BRJARVIS\Br-Jarvis/events/types.py) | `65` | `BaseEvent`, `SystemEvent`, `TaskEvent`, `AuditEvent`, `ErrorEvent`, `VoiceEvent`, `ToolExecutionEvent`, `VisionEvent` | — | Core subsystem module |

### 3.10 Subsystem: `guardian/`
**Description**: Immutable Security Governance, Path Policy Enforcement, SHA256 Hashing, Kill Switch & Rollback
**Total Modules**: 6

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/guardian/__init__.py) | `18` | — | — | Guardian Core Subsystem for BR JARVIS. Enforces system integrity, kill-switch pauses, snapshot retention, automated roll |
| [audit_log.py](file:///d:\BRJARVIS\Br-Jarvis/guardian/audit_log.py) | `84` | `AuditLog` | — | Append-only Audit Log for autonomous actions, self-upgrades, and routing shifts. Includes automatic log file rotation. |
| [core.py](file:///d:\BRJARVIS\Br-Jarvis/guardian/core.py) | `127` | `GuardianCore` | `get_guardian_core()` | Core subsystem module |
| [kill_switch.py](file:///d:\BRJARVIS\Br-Jarvis/guardian/kill_switch.py) | `56` | `KillSwitch` | — | Global Emergency Pause Switch for Autonomous Operations. Monitors flag files, CLI pause triggers, and hotkeys. |
| [rollback.py](file:///d:\BRJARVIS\Br-Jarvis/guardian/rollback.py) | `63` | `RollbackEngine` | — | Automatic Rollback Engine that restores system state on failed healthchecks. |
| [snapshot.py](file:///d:\BRJARVIS\Br-Jarvis/guardian/snapshot.py) | `83` | `SnapshotManager` | — | Manages pre-upgrade git commits, database backups, and rolling snapshot retention. |

### 3.11 Subsystem: `history/`
**Description**: Session Persistence Store, Trajectory Replay Engine & Audit Writer
**Total Modules**: 5

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/history/__init__.py) | `23` | — | — | Provides:   - SessionStore    — SQLite-backed session and turn storage   - HistoryLinker   — ChromaDB semantic session l |
| [audit_writer.py](file:///d:\BRJARVIS\Br-Jarvis/history/audit_writer.py) | `148` | — | `set_session_id()`, `_rotate_if_needed()`, `_truncate_args()` | Structured JSON audit writer for JARVIS MK37.  Writes to:   ~/.jarvis/history/audit.jsonl  — structured JSON Lines (mach |
| [linker.py](file:///d:\BRJARVIS\Br-Jarvis/history/linker.py) | `198` | `HistoryLinker` | — | Semantic session linker using ChromaDB or TF-IDF fallback.  On session close, the session summary is embedded into a vec |
| [replay.py](file:///d:\BRJARVIS\Br-Jarvis/history/replay.py) | `255` | — | `load_session()`, `replay_as_context()`, `export_markdown()` | Session replay and export utilities for JARVIS MK37.  Reconstructs WorkingMemory objects from stored turns and exports s |
| [session_store.py](file:///d:\BRJARVIS\Br-Jarvis/history/session_store.py) | `356` | `SessionStore` | — | SQLite-backed persistent session and turn storage for JARVIS MK37.  Storage location: ~/.jarvis/history/sessions.db  Sch |

### 3.12 Subsystem: `memory/`
**Description**: 5-Tier Memory & Knowledge System (SQLite WAL, ChromaDB, Temporal KG 2.0, Ebbinghaus Decay, Experience Replay)
**Total Modules**: 21

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/memory/__init__.py) | `15` | — | — | Core subsystem module |
| [archiver.py](file:///d:\BRJARVIS\Br-Jarvis/memory/archiver.py) | `51` | `MemoryArchiver` | — | Core subsystem module |
| [cache.py](file:///d:\BRJARVIS\Br-Jarvis/memory/cache.py) | `79` | `CacheEntry`, `MemoryCache` | — | Core subsystem module |
| [config_manager.py](file:///d:\BRJARVIS\Br-Jarvis/memory/config_manager.py) | `91` | — | `get_base_dir()`, `ensure_config_dir()`, `config_exists()` | Core subsystem module |
| [consolidator.py](file:///d:\BRJARVIS\Br-Jarvis/memory/consolidator.py) | `139` | — | `consolidate_session()` | Memory consolidator: extract long-term insights from completed sessions. Ported from the Claude Code collection for JARV |
| [contact_manager.py](file:///d:\BRJARVIS\Br-Jarvis/memory/contact_manager.py) | `722` | `ContactCipher`, `UnifiedContactStore` | `get_base_dir()`, `mask_phone()`, `mask_email()` | Unified Contact Store Manager for BR JARVIS. Supports parsing and importing mobile contacts from: - Primary System vCard |
| [conversation_store.py](file:///d:\BRJARVIS\Br-Jarvis/memory/conversation_store.py) | `219` | `ConversationStore` | — | SQLite-backed conversation history store for JARVIS MK37. Replaces slow file-based audits/sessions with queryable databa |
| [decay.py](file:///d:\BRJARVIS\Br-Jarvis/memory/decay.py) | `67` | `MemoryItem`, `MemoryDecayEngine` | — | Implements Ebbinghaus memory decay: RetentionScore = Importance * e^(-decay_rate * elapsed_time) * (1 + access_frequency |
| [experience_replay.py](file:///d:\BRJARVIS\Br-Jarvis/memory/experience_replay.py) | `177` | `ExperienceTrajectory`, `ExperienceReplayStore` | `get_experience_replay()` | Stores complete execution trajectories (successful vs failed steps) in SQLite WAL database for trajectory playback, simi |
| [knowledge_graph.py](file:///d:\BRJARVIS\Br-Jarvis/memory/knowledge_graph.py) | `153` | `KnowledgeGraph` | `get_knowledge_graph()` | KnowledgeGraph provides a graph-based world model connecting workspace entities, projects, files, apps, windows, goals,  |
| [lessons.py](file:///d:\BRJARVIS\Br-Jarvis/memory/lessons.py) | `98` | `LessonStore` | — | LessonStore for storing and semantically retrieving explicit and implicit user corrections. Used by ContextEngine at Pri |
| [memory_context.py](file:///d:\BRJARVIS\Br-Jarvis/memory/memory_context.py) | `134` | — | `truncate_index_content()`, `get_memory_context()`, `find_relevant_memories()` | Memory context building for system prompt injection. Ported & enhanced for JARVIS MK37.  Provides:   get_memory_context( |
| [memory_manager.py](file:///d:\BRJARVIS\Br-Jarvis/memory/memory_manager.py) | `303` | — | `get_base_dir()`, `_empty_memory()`, `load_memory()` | Working memory manager for JARVIS MK37 (voice interface).  BUG-FIX (Minor — dict mutation during iteration):   `_trim_to |
| [memory_scan.py](file:///d:\BRJARVIS\Br-Jarvis/memory/memory_scan.py) | `111` | `MemoryHeader` | `scan_memory_dir()`, `scan_all_memories()`, `memory_age_days()` | Memory file scanning with mtime tracking and freshness/age helpers. Ported from the Claude Code collection for JARVIS MK |
| [memory_types.py](file:///d:\BRJARVIS\Br-Jarvis/memory/memory_types.py) | `64` | — | — | Memory type taxonomy and system-prompt guidance text. Ported from the Claude Code collection for JARVIS MK37.  Four type |
| [persistent_store.py](file:///d:\BRJARVIS\Br-Jarvis/memory/persistent_store.py) | `464` | `MemoryEntry` | `get_project_memory_dir()`, `get_memory_dir()`, `_slugify()` | File-based persistent memory storage with user-level and project-level scopes. Ported & enhanced for JARVIS MK37.  Stora |
| [reflection.py](file:///d:\BRJARVIS\Br-Jarvis/memory/reflection.py) | `90` | `ReflectionEngine` | — | ReflectionEngine for analyzing user feedback, implicit re-prompts, tool failures, and failed steps, automatically writin |
| [temporal_kg.py](file:///d:\BRJARVIS\Br-Jarvis/memory/temporal_kg.py) | `131` | `TemporalEdge`, `TemporalKnowledgeGraph` | `get_temporal_kg()` | Extends relational world modeling by storing time-stamped edges (e1, r, e2, t_start, t_end) for temporal queries, state  |
| [unified_memory.py](file:///d:\BRJARVIS\Br-Jarvis/memory/unified_memory.py) | `171` | `UnifiedMemoryManager` | `get_unified_memory()` | Core subsystem module |
| [vector_store.py](file:///d:\BRJARVIS\Br-Jarvis/memory/vector_store.py) | `247` | `GeminiEmbeddingFunction`, `TextSimilarityMemory`, `VectorMemory` | — | ChromaDB-backed vector memory for JARVIS MK37. Uses Google GenAI API for fast embeddings (text-embedding-004), with a pu |
| [working.py](file:///d:\BRJARVIS\Br-Jarvis/memory/working.py) | `60` | `WorkingMemory` | — | Core subsystem module |

### 3.13 Subsystem: `multi_agent/`
**Description**: Sub-Agent Framework & Autonomous Task Delegation
**Total Modules**: 2

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/multi_agent/__init__.py) | `19` | — | — | Multi-Agent Orchestration & Sub-Agent Task Management Package. |
| [subagent.py](file:///d:\BRJARVIS\Br-Jarvis/multi_agent/subagent.py) | `147` | `AgentDefinition`, `SubAgentTask`, `SubAgentManager` | `load_agent_definitions()`, `get_agent_definition()` | Sub-Agent Registry and Manager for BR-Jarvis. Manages specialized multi-agent sub-delegation (Code Engineer, Security Au |

### 3.14 Subsystem: `orchestrator/`
**Description**: ReAct Orchestration Loop, Speculative Task Coordinator & Context Resolver
**Total Modules**: 3

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/orchestrator/__init__.py) | `13` | — | — | Re-exports JarvisOrchestrator and speculative components for unified import. |
| [core.py](file:///d:\BRJARVIS\Br-Jarvis/orchestrator/core.py) | `747` | `JarvisOrchestrator` | `_format_clean_tool_summary()` | ReAct (Reason + Act) orchestration loop powered by Gemini. |
| [speculative.py](file:///d:\BRJARVIS\Br-Jarvis/orchestrator/speculative.py) | `18` | — | — | Implements speculative drafting and parallel validation to accelerate tool step execution loops. Re-exports from reasoni |

### 3.15 Subsystem: `plugins/`
**Description**: Plugin Isolation Manager & Tool Registry Bridge
**Total Modules**: 2

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/plugins/__init__.py) | `28` | — | `load_custom_plugins()` | Core subsystem module |
| [plugin_manager.py](file:///d:\BRJARVIS\Br-Jarvis/plugins/plugin_manager.py) | `126` | `PluginStatus`, `PluginMetadata`, `PluginManager` | `get_plugin_manager()` | Core subsystem module |

### 3.16 Subsystem: `reasoning/`
**Description**: Meta-Cognition Engine, Speculative Execution Core, Cognitive Loop & Prompt Cache
**Total Modules**: 9

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/__init__.py) | `23` | — | — | Reasoning engine package providing Chain-of-Thought (CoT), Task Graph generation, confidence scoring, and self-verificat |
| [cognitive_loop.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/cognitive_loop.py) | `92` | `SelfEvaluationPayload`, `CognitiveLoop` | `get_cognitive_loop()` | Implements explicit Observe -> Think -> Critic -> Improve -> Retry cognitive loop for BR JARVIS step execution evaluatio |
| [engine.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/engine.py) | `185` | `ReasoningEngine` | `get_reasoning_engine()` | Core subsystem module |
| [meta_cognition.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/meta_cognition.py) | `117` | `MetaCognitiveAssessment`, `MetaCognitionEngine` | `get_meta_cognition()` | Pre-execution meta-cognitive evaluation layer predicting execution risk, CoT depth, context completeness, and goal feasi |
| [prompt_cache.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/prompt_cache.py) | `63` | `PromptCacheManager` | — | High-performance prompt caching & token budget manager. Hashes system prompts and history context blocks using SHA-256 t |
| [speculative.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/speculative.py) | `117` | `SpeculativeDraftStep`, `SpeculativeExecutionEngine` | `get_speculative_engine()` | Implements speculative drafting and parallel validation to accelerate tool step execution loops. |
| [speculative_engine.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/speculative_engine.py) | `43` | `SpeculativeEngine` | — | Fast-path speculative tool execution engine. Performs lightweight rule-based pattern matching to speculate tool intent b |
| [speculative_selector.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/speculative_selector.py) | `37` | `SpeculativeModelSelector` | — | Speculative Model Speed-Quality Selector for JARVIS. Evaluates query complexity, latency targets, and token budget to dy |
| [types.py](file:///d:\BRJARVIS\Br-Jarvis/reasoning/types.py) | `92` | `StepStatus`, `ConfidenceScore`, `TaskNode`, `PlanGraph`, `ReasoningStep`, `ReasoningTrace` | — | Core subsystem module |

### 3.17 Subsystem: `redteam/`
**Description**: Local Recon Scanner, Vulnerability Auditor & Security Scope Governance
**Total Modules**: 5

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/redteam/__init__.py) | `1` | — | — | Core subsystem module |
| [recon.py](file:///d:\BRJARVIS\Br-Jarvis/redteam/recon.py) | `75` | `ReconEngine` | — | Core subsystem module |
| [report.py](file:///d:\BRJARVIS\Br-Jarvis/redteam/report.py) | `109` | — | `generate_report()`, `generate_html_report()` | Core subsystem module |
| [scope.py](file:///d:\BRJARVIS\Br-Jarvis/redteam/scope.py) | `61` | `ScopeEnforcer` | — | Core subsystem module |
| [vuln_scanner.py](file:///d:\BRJARVIS\Br-Jarvis/redteam/vuln_scanner.py) | `48` | `VulnScanner` | — | Core subsystem module |

### 3.18 Subsystem: `root/`
**Description**: Root Core Infrastructure & System Launchers (Entry points, CLI, Server, Base Specs)
**Total Modules**: 12

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [BR.spec](file:///d:\BRJARVIS\Br-Jarvis/BR.spec) | `57` | — | — | Core subsystem module |
| [main_mk37.py](file:///d:\BRJARVIS\Br-Jarvis/main_mk37.py) | `387` | — | `_print_banner()`, `_print_help()`, `_handle_parallel_run()` | Interactive CLI REPL for BR JARVIS MK37. Features: - Gemini-native ReAct orchestration loop with streaming response - Pa |
| [permissions.py](file:///d:\BRJARVIS\Br-Jarvis/permissions.py) | `209` | `PermissionMode`, `PermissionPolicy`, `PathTier`, `PathPolicy` | `_normalize_mode()`, `_load_scope_defaults()`, `_build_global_policy()` | Permission policy compatibility layer for JARVIS MK37.  This module keeps the historical top-level ``permissions`` impor |
| [pyproject.toml](file:///d:\BRJARVIS\Br-Jarvis/pyproject.toml) | `144` | — | — | Core subsystem module |
| [pytest.ini](file:///d:\BRJARVIS\Br-Jarvis/pytest.ini) | `9` | — | — | Core subsystem module |
| [requirements.txt](file:///d:\BRJARVIS\Br-Jarvis/requirements.txt) | `42` | — | — | Core subsystem module |
| [server.py](file:///d:\BRJARVIS\Br-Jarvis/server.py) | `920` | `WSBroadcastStream`, `ChatRequest`, `RememberRequest`, `RunRequest`, `SwitchBackendRequest`, `SaveMemoryRequest`, `OpenAIChatMessage`, `OpenAIChatRequest`, `VoiceTTSRequest` | `_strip_rich()`, `main()` | FastAPI Server for JARVIS MK37. Exposes REST and WebSocket endpoints for dashboard, voice sync, and OpenAI-compatible AP |
| [setup.py](file:///d:\BRJARVIS\Br-Jarvis/setup.py) | `11` | — | — | Core subsystem module |
| [setup_linux.sh](file:///d:\BRJARVIS\Br-Jarvis/setup_linux.sh) | `69` | — | — | Core subsystem module |
| [start.py](file:///d:\BRJARVIS\Br-Jarvis/start.py) | `1047` | `EnvStatus` | `_banner()`, `_check_env()`, `_check_module()` | Core subsystem module |
| [startup.bat](file:///d:\BRJARVIS\Br-Jarvis/startup.bat) | `67` | — | — | Core subsystem module |
| [ui_mark.py](file:///d:\BRJARVIS\Br-Jarvis/ui_mark.py) | `3631` | `C`, `_SysMetrics`, `HudCanvas`, `MetricBar`, `LogWidget`, `SubAgentTaskWidget`, `SubAgentTaskPanel`, `FileDropZone`, `_DropCanvas`, `_CameraPreview`, `SetupOverlay`, `HueWheel`, `CustomizeOverlay`, `ClipboardPanel`, `RemoteKeyOverlay`, `MainWindow`, `_RootShim`, `JarvisUI` | `_base_dir()`, `_read_full_config()`, `apply_ui_accent()` | Core subsystem module |

### 3.19 Subsystem: `router/`
**Description**: Dynamic Multi-Backend AI Model Router (Quality, Latency, Cost Routing)
**Total Modules**: 2

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/router/__init__.py) | `15` | — | — | Re-exports AgentRouter and AgentProfile for unified import. |
| [core.py](file:///d:\BRJARVIS\Br-Jarvis/router/core.py) | `214` | `AgentProfile`, `AgentRouter` | `_get_configured_default()`, `load_available_backends()`, `get_router()` | Intelligent routing with Gemini as the primary (and only required) backend. |

### 3.20 Subsystem: `screen_server/`
**Description**: Real-Time WebSocket Screen Frame Streaming Server
**Total Modules**: 2

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/screen_server/__init__.py) | `6` | — | — | Provides:   - ScreenShareServer — asyncio WebSocket server for broadcasting screen frames |
| [ws_server.py](file:///d:\BRJARVIS\Br-Jarvis/screen_server/ws_server.py) | `143` | `ScreenShareServer` | — | Core subsystem module |

### 3.21 Subsystem: `scripts/`
**Description**: Build, Setup, Migration, Audit & Smoke Testing Utilities
**Total Modules**: 17

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/__init__.py) | `5` | — | — | Build, migration, and test scripts. |
| [build_app.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/build_app.py) | `72` | — | `build_app()` | Multi-Platform App Builder for BR JARVIS (Windows, Linux, macOS, Web/PWA). Bundles native dependencies, web frontend ass |
| [deep_audit_flaws.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/deep_audit_flaws.py) | `57` | — | — | Core subsystem module |
| [install_startup.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/install_startup.py) | `246` | — | `get_project_dir()`, `install_linux()`, `install_mac()` | Installs BR JARVIS MK37 into auto-startup across Windows, Linux, and macOS. - On Linux: Creates XDG Autostart entry (~/. |
| [migrate_memory.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/migrate_memory.py) | `93` | — | `migrate()` | Migration script: seed ChromaDB vector store from existing JSON/file memory.  Reads all .md memory files from ~/.jarvis/ |
| [probe_voice_env.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/probe_voice_env.py) | `12` | — | — | Core subsystem module |
| [reformat_skills_library.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/reformat_skills_library.py) | `137` | — | `clean_skill_name()`, `format_domain()`, `generate_triggers()` | Automated Skill Library Transformer for BR JARVIS. Standardizes YAML frontmatter, category, domain, triggers, BR JARVIS  |
| [setup_native.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/setup_native.py) | `164` | — | `find_compiler()`, `auto_install_compiler()`, `compile_native()` | Compiles native/jarvis_native.c into shared library (libjarvis_native.so / .dll / .dylib). Includes multi-method auto-in |
| [setup_upgrade.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/setup_upgrade.py) | `235` | — | `_resolve_target_dir()`, `print_step()`, `print_ok()` | Applies the Gemini-native upgrade to your JARVIS MK37 installation. Run from your JARVIS project root:     python setup_ |
| [simulate_voice_listening.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/simulate_voice_listening.py) | `67` | — | — | Core subsystem module |
| [smoke_startup.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/smoke_startup.py) | `132` | — | `_repo_root()`, `_check()`, `main()` | Non-destructive startup smoke checks for JARVIS MK37.  This script validates core imports and lightweight runtime invari |
| [test_all_models.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/test_all_models.py) | `70` | — | — | Core subsystem module |
| [test_jarvis_suite.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/test_jarvis_suite.py) | `137` | — | `run_full_suite()` | Executes full end-to-end integration test matrix for BR JARVIS features: 1. 0-Token Intent Engine & Excel Analysis Expor |
| [test_new_jarvis.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/test_new_jarvis.py) | `75` | — | `test_note_scoring_offline()`, `main()` | Core subsystem module |
| [test_scoring_breakdown.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/test_scoring_breakdown.py) | `20` | — | — | Core subsystem module |
| [test_toughest_tasks.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/test_toughest_tasks.py) | `330` | — | `log_result()`, `test_1_voice_fallback()`, `test_2_cli_reasoning()` | Core subsystem module |
| [verify_complexity_routing.py](file:///d:\BRJARVIS\Br-Jarvis/scripts/verify_complexity_routing.py) | `22` | — | — | Core subsystem module |

### 3.22 Subsystem: `skills/`
**Description**: Dynamic Skill & Plugin Engine (Hot Reload, Skill Registry, Builtin RAG & Writer Skills)
**Total Modules**: 13

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/skills/__init__.py) | `33` | — | — | Skills are markdown files with YAML frontmatter that define reusable prompt templates. They can be loaded from multiple  |
| [builtin.py](file:///d:\BRJARVIS\Br-Jarvis/skills/builtin.py) | `337` | — | `_register_builtins()` | Built-in skills that ship with JARVIS MK37. Importing this module registers all built-in skills into the loader. |
| [builtin_connectors.py](file:///d:\BRJARVIS\Br-Jarvis/skills/builtin_connectors.py) | `106` | — | `load_builtin_connector_skills()` | Built-in skill definitions for Gmail, Notion, GitHub, Google Calendar, and Slack. |
| [builtin_editor.py](file:///d:\BRJARVIS\Br-Jarvis/skills/builtin_editor.py) | `174` | — | `_register_editor_builtins()` | Built-in editor skills for JARVIS MK37. These skills combine the file tools with PC control to operate code editors (VS  |
| [builtin_extras.py](file:///d:\BRJARVIS\Br-Jarvis/skills/builtin_extras.py) | `435` | — | `_register_extra_builtins()` | Extra built-in skills for JARVIS MK37. Importing this module registers 5 additional skills:   - github_scan      — Scan  |
| [builtin_pro.py](file:///d:\BRJARVIS\Br-Jarvis/skills/builtin_pro.py) | `1006` | — | `_register_pro_skills()` | Professional skill collection for JARVIS MK37. 30 production-ready skills covering: DevOps, Security, Analysis, Producti |
| [builtin_rag.py](file:///d:\BRJARVIS\Br-Jarvis/skills/builtin_rag.py) | `96` | — | — | RAG (Retrieval-Augmented Generation) skills for JARVIS MK37. Importing this module registers skills for document chat, l |
| [builtin_writer.py](file:///d:\BRJARVIS\Br-Jarvis/skills/builtin_writer.py) | `305` | — | — | Professional writing assistant skills collection for JARVIS MK37. Covers: academic writing, creative writing, email draf |
| [executor.py](file:///d:\BRJARVIS\Br-Jarvis/skills/executor.py) | `81` | — | `execute_skill()`, `_execute_inline()`, `_execute_forked()` | Skill execution: inline (current conversation) or forked (sub-agent). Adapted from the Claude Code collection for JARVIS |
| [hot_reload.py](file:///d:\BRJARVIS\Br-Jarvis/skills/hot_reload.py) | `62` | `SkillHotReloader` | — | Dynamic Skill Hot-Reload Engine for BR JARVIS. Monitors skills/ and .agents/skills directories to hot-reload new user-in |
| [installer.py](file:///d:\BRJARVIS\Br-Jarvis/skills/installer.py) | `353` | — | `_ensure_dirs()`, `_load_registry()`, `_save_registry()` | JARVIS MK37 Skill Installer — Fetch, convert, and install external skills.  Supports:   - Git-based skill packs (claude- |
| [loader.py](file:///d:\BRJARVIS\Br-Jarvis/skills/loader.py) | `258` | `SkillDef` | `_get_skill_paths()`, `_parse_list_field()`, `_parse_skill_file()` | Skill loading: parse markdown files with YAML frontmatter into SkillDef objects. Adapted from the Claude Code collection |
| [registry.py](file:///d:\BRJARVIS\Br-Jarvis/skills/registry.py) | `81` | — | `_get_cached_skills()`, `get_all_skills()`, `get_skills_by_category()` | Skill Registry: High-level search, category grouping, and discovery interface for BR JARVIS's 400+ domain skills. |

### 3.23 Subsystem: `tests/`
**Description**: Master Automated Pytest Suite & Integration Test Infrastructure
**Total Modules**: 54

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/tests/__init__.py) | `1` | — | — | Core subsystem module |
| [test_antigravity_system.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_antigravity_system.py) | `105` | `TestAntigravitySystem` | — | Core subsystem module |
| [test_autonomous_browser_agent.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_autonomous_browser_agent.py) | `14` | — | `test_autonomous_browser_tools_importable()` | Core subsystem module |
| [test_browser_automation.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_browser_automation.py) | `36` | — | `test_web_app_tool_schemas()`, `test_gmail_tool_definitions()`, `test_full_browser_control_tools()` | Core subsystem module |
| [test_claude_skills_integration.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_claude_skills_integration.py) | `46` | `TestClaudeSkillsIntegration` | — | Core subsystem module |
| [test_clipboard_read.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_clipboard_read.py) | `65` | `TestClipboardUtils` | — | Core subsystem module |
| [test_complexity_router.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_complexity_router.py) | `88` | — | `test_fast_complexity()`, `test_medium_complexity()`, `test_high_complexity_code()` | Core subsystem module |
| [test_computer_operator.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_computer_operator.py) | `31` | — | `test_computer_operator_execution()` | Core subsystem module |
| [test_contact_importer.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_contact_importer.py) | `93` | — | `temp_contact_store()`, `test_vcf_import()`, `test_csv_import()` | Unit and integration tests for UnifiedContactStore, vCard/CSV parsing, fuzzy name resolution, and multi-file knowledge i |
| [test_context_engine.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_context_engine.py) | `69` | — | `test_token_counter()`, `test_context_compressor()`, `test_context_builder()` | Core subsystem module |
| [test_core_runtime.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_core_runtime.py) | `102` | — | `test_pydantic_config_loading()`, `test_dependency_injection_container()`, `test_health_monitor()` | Core subsystem module |
| [test_deep_audit.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_deep_audit.py) | `553` | — | `_run_audit()`, `t_perm_allow_all()`, `t_perm_global_singleton()` | JARVIS MK37 -- Deep Audit: Runtime cross-reference and logic bug test. |
| [test_duplicate_call_guard.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_duplicate_call_guard.py) | `31` | — | `test_duplicate_call_guard_and_memory_turn()` | Core subsystem module |
| [test_event_bus.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_event_bus.py) | `61` | — | — | Core subsystem module |
| [test_executor_engine.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_executor_engine.py) | `41` | — | — | Core subsystem module |
| [test_galaxy_integration.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_galaxy_integration.py) | `33` | — | `test_ensure_sample_notes()`, `test_scan_markdown_notes()`, `test_galaxy_chat()` | Core subsystem module |
| [test_gemini_stt.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_gemini_stt.py) | `17` | — | `test_get_listen_api_key()`, `test_transcribe_audio_online_fallback_on_invalid()`, `test_transcribe_audio_online_fallback_on_junk_bytes()` | Core subsystem module |
| [test_gmail_auth.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_gmail_auth.py) | `82` | `TestGmailAuth` | — | Automated unit & integration test suite verifying Gmail authentication, credential storage, browser sign-in trigger, log |
| [test_guardian.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_guardian.py) | `74` | `TestGuardianSafety` | — | Unit tests for Guardian Core, KillSwitch, SnapshotManager, RollbackEngine, and PathPolicy. |
| [test_implementation_upgrades.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_implementation_upgrades.py) | `42` | — | `test_tool_prompt_pruning()`, `test_cdp_dom_bridge_init()`, `test_compat_backend_import()` | Verification tests for: - Pruned tool prompt block token reduction - CDP Browser DOM Bridge availability and graph struc |
| [test_integration.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_integration.py) | `126` | — | `run_integration_tests()` | JARVIS MK37 — Full Integration Test Suite. |
| [test_intent_whatsapp.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_intent_whatsapp.py) | `65` | — | `test_whatsapp_intent_say_to_appa()`, `test_whatsapp_intent_send_hi_to_mom()`, `test_whatsapp_intent_colon_format()` | Unit tests verifying zero-token deterministic intent routing for WhatsApp voice commands. |
| [test_markl_integration.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_markl_integration.py) | `45` | — | `test_background_monitor()`, `test_proactive_engine()`, `test_file_processor_detect_type()` | Core subsystem module |
| [test_markui.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_markui.py) | `17` | — | `test_ui_mark_importable()`, `test_ui_mark_palette()` | Core subsystem module |
| [test_master_suite.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_master_suite.py) | `63` | `TestMasterSuiteRunner` | `run_master_suite()` | Master Test Suite Runner consolidating all 80+ unit & integration tests across 5 major domains: 1. Antigravity Agent Cor |
| [test_memory_engine.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_memory_engine.py) | `47` | — | `test_memory_cache_hit_and_expiry()`, `test_memory_archiver_consolidation()`, `test_unified_memory_manager()` | Core subsystem module |
| [test_mk38_phase1_upgrades.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_mk38_phase1_upgrades.py) | `76` | — | `test_meta_cognition_eval()`, `test_speculative_execution()`, `test_experience_replay_store()` | Core subsystem module |
| [test_mk38_phase2_upgrades.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_mk38_phase2_upgrades.py) | `70` | — | `test_temporal_knowledge_graph()`, `test_workspace_code_graph()` | Core subsystem module |
| [test_multi_channel_intent.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_multi_channel_intent.py) | `59` | — | `test_multi_channel_whatsapp_and_gmail()`, `test_standalone_email_intent()` | Unit tests verifying zero-token multi-channel compound intent routing (WhatsApp + Gmail) and standalone email/gmail inte |
| [test_offline_voice.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_offline_voice.py) | `32` | — | `test_wake_phrase_detection()`, `test_command_extraction_from_wake()` | Core subsystem module |
| [test_phase4_features.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_phase4_features.py) | `29` | `TestPhase4Features` | — | Core subsystem module |
| [test_planner_engine.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_planner_engine.py) | `41` | — | `test_planner_engine_risk_assessment()`, `test_planner_replanning()` | Core subsystem module |
| [test_plugin_manager.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_plugin_manager.py) | `29` | — | `test_plugin_manager_discovery()` | Core subsystem module |
| [test_prompt_pack_integration.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_prompt_pack_integration.py) | `20` | — | `test_galaxy_graph_build()`, `test_remember_that_tool()`, `test_boot_briefing()` | Core subsystem module |
| [test_qa_testing_tool.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_qa_testing_tool.py) | `36` | — | `test_qa_tool_handlers_importable()`, `test_qa_generate_report_output()` | Core subsystem module |
| [test_regression_fixes.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_regression_fixes.py) | `59` | `TestRegressionFixes` | — | Core subsystem module |
| [test_relationship_resolution.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_relationship_resolution.py) | `67` | — | `relationship_store()`, `test_contact_store_relationship_resolution()`, `test_whatsapp_recipient_resolution()` | Unit tests for multilingual relationship alias resolution ("Appa", "Amma", "Dad", "Mom") across UnifiedContactStore, Wha |
| [test_semantic_vision.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_semantic_vision.py) | `94` | — | `test_semantic_types()`, `test_accessibility_bridge()`, `test_ocr_engine_lru_cache()` | Core subsystem module |
| [test_server_web.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_server_web.py) | `58` | — | `client()`, `test_health_endpoint()`, `test_api_status_endpoint()` | Core subsystem module |
| [test_smart_email_sender.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_smart_email_sender.py) | `89` | `TestSmartEmailSender` | — | Automated unit & integration test suite verifying smart email composition, recipient resolution, contact storage, schedu |
| [test_step_planner.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_step_planner.py) | `59` | `TestStepPlanner` | — | Core subsystem module |
| [test_stt_variations.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_stt_variations.py) | `38` | — | `test_stt_missing_to_and_double_i()`, `test_tool_pruning_includes_send_whatsapp_on_stt_watsapp()` | Unit tests verifying zero-token execution for spoken STT variations ("hii", missing "to", "watsapp....") and ensuring se |
| [test_system_resilience.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_system_resilience.py) | `28` | — | `test_sounddevice_mic_invalid_device_fallback()`, `test_tts_stop_resilience()` | Core subsystem module |
| [test_system_upgrades_v4.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_system_upgrades_v4.py) | `41` | `TestSystemUpgradesV4` | — | Core subsystem module |
| [test_tool_runtime.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_tool_runtime.py) | `60` | — | `test_tool_runtime_list_tools()` | Core subsystem module |
| [test_tool_suite_audit.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_tool_suite_audit.py) | `77` | `TestToolSuiteAudit` | — | Core subsystem module |
| [test_ui_mark.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_ui_mark.py) | `27` | `TestUIMark` | — | Core subsystem module |
| [test_ui_multitask.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_ui_multitask.py) | `56` | `TestUIMultiTask` | — | Core subsystem module |
| [test_ultrafast_wake.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_ultrafast_wake.py) | `44` | `TestUltrafastWakeDetection` | — | Core subsystem module |
| [test_vision_engine.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_vision_engine.py) | `46` | — | `test_screen_analyst_capture()`, `test_ocr_engine()`, `test_vision_engine_analysis()` | Core subsystem module |
| [test_voice_latency.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_voice_latency.py) | `89` | — | `test_silero_vad_latency()`, `test_in_memory_whisper_performance()`, `test_async_registry_safety()` | Performance and functional verification test for BR JARVIS MK37 Voice Subsystem. Tests: - Silero VAD detection latency & |
| [test_voice_pipeline.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_voice_pipeline.py) | `120` | `TestVoicePipeline` | — | Core subsystem module |
| [test_walkthrough_tool.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_walkthrough_tool.py) | `27` | — | `test_generate_walkthrough_tool()` | Core subsystem module |
| [test_whatsapp_calendar_automation.py](file:///d:\BRJARVIS\Br-Jarvis/tests/test_whatsapp_calendar_automation.py) | `116` | `TestWhatsAppCalendarAutomation` | — | Automated unit & integration test suite verifying WhatsApp contact messaging, scheduled messaging queues, natural langua |

### 3.24 Subsystem: `tests/integration/`
**Description**: Integration Test Suites (OCR, Vision, Stability, File Terminal)
**Total Modules**: 6

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/tests/integration/__init__.py) | `2` | — | — | Core subsystem module |
| [test_file_terminal.py](file:///d:\BRJARVIS\Br-Jarvis/tests/integration/test_file_terminal.py) | `42` | — | `test_scenario_10_file_operations()`, `test_scenario_11_12_terminal_and_git()` | Core subsystem module |
| [test_memory_context.py](file:///d:\BRJARVIS\Br-Jarvis/tests/integration/test_memory_context.py) | `66` | — | `test_scenario_23_context_persistence()`, `test_scenario_24_event_logging()`, `test_scenario_26_memory_recall()` | Core subsystem module |
| [test_ocr_accuracy.py](file:///d:\BRJARVIS\Br-Jarvis/tests/integration/test_ocr_accuracy.py) | `41` | — | `test_scenario_17_ocr_accuracy()`, `test_scenario_18_handwritten_ocr()`, `test_scenario_19_ocr_noisy_background()` | Core subsystem module |
| [test_stability.py](file:///d:\BRJARVIS\Br-Jarvis/tests/integration/test_stability.py) | `98` | — | — | Core subsystem module |
| [test_vision_operator.py](file:///d:\BRJARVIS\Br-Jarvis/tests/integration/test_vision_operator.py) | `134` | — | `test_scenario_1_to_2_open_app_and_calculation()`, `test_scenario_3_copy_paste_text()`, `test_scenario_5_to_6_multimonitor_and_screen_hash()` | Core subsystem module |

### 3.25 Subsystem: `tools/`
**Description**: Tool Ecosystem (98+ Tools), Runtime, MCP Connector, Browser Agent, Code Tools & Diagnostic Suite
**Total Modules**: 56

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/tools/__init__.py) | `25` | — | — | Universal tool package re-exporting key registry functions and schemas. |
| [agent_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/agent_tools.py) | `174` | — | `_get_subagent_manager()`, `tool_spawn_agent()`, `tool_send_message()` | Sub-agent management tools plugin for JARVIS MK37. Allows spawning, message-passing, and monitoring autonomous sub-agent |
| [app_analyzer_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/app_analyzer_tools.py) | `113` | — | `tool_list_installed_applications()`, `tool_list_running_applications()`, `tool_search_applications()` | System Application Analyzer Tools Plugin for JARVIS. Exposes tools for scanning installed software and running process a |
| [app_connectors.py](file:///d:\BRJARVIS\Br-Jarvis/tools/app_connectors.py) | `321` | — | `gmail_list_unread()`, `gmail_send_email()`, `notion_search_pages()` | App Connectors for external productivity tools and cloud platforms. Supports Gmail, Notion, GitHub, Google Calendar, Sla |
| [app_tracker_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/app_tracker_tools.py) | `76` | — | `tool_get_app_launch_history()`, `tool_get_app_usage_statistics()` | Application Launch Tracker Tools Plugin for JARVIS. Exposes tools for querying application start history logs and usage  |
| [audit_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/audit_tools.py) | `91` | — | `_get_workspace_dir()`, `audit_codebase()` | Codebase Auditor, Security Vulnerability Scanner, and Code Quality Suite. |
| [automation_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/automation_tools.py) | `112` | — | `tool_automate_app()`, `tool_run_automation_workflow()`, `tool_execute_system_automation()` | Automation Engine Tools Plugin for JARVIS. Exposes application automation, workflow macro scripting, and system command  |
| [autonomous_browser_agent.py](file:///d:\BRJARVIS\Br-Jarvis/tools/autonomous_browser_agent.py) | `223` | — | `browser_execute_web_task()`, `browser_auto_navigate_and_extract()`, `browser_fill_and_submit_form()` | Autonomous Web Task Agent for BR JARVIS. Controls a background Playwright browser to execute end-to-end user-assigned we |
| [background_monitor_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/background_monitor_tools.py) | `59` | — | `tool_add_background_monitor()`, `tool_remove_background_monitor()`, `tool_list_monitored_topics()` | Core subsystem module |
| [batch_file_tool.py](file:///d:\BRJARVIS\Br-Jarvis/tools/batch_file_tool.py) | `122` | — | `batch_file_ops()` | Provides directory tree visualization, batch regex search and replace across files, and zip archive operations. |
| [browser_automation.py](file:///d:\BRJARVIS\Br-Jarvis/tools/browser_automation.py) | `463` | — | `get_browser_trace_logs()`, `clear_browser_trace_logs()`, `_attach_trace_listeners()` | Playwright-driven interactive browser controller with session persistence for Gmail, Microsoft 365, Outlook, and general |
| [calendar_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/calendar_tools.py) | `145` | — | `tool_create_calendar_event()`, `tool_list_calendar_events()`, `tool_search_calendar_events()` | Calendar & Task Tools Plugin for JARVIS. Exposes tools for creating calendar events, listing upcoming tasks, searching e |
| [code_refactor_tool.py](file:///d:\BRJARVIS\Br-Jarvis/tools/code_refactor_tool.py) | `118` | — | `code_refactor()` | Provides python code analysis, AST parsing, syntax validation, refactoring suggestions, and code formatting tools. |
| [code_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/code_tools.py) | `32` | — | `tool_run_code()` | Code execution/sandbox tools plugin for JARVIS MK37. Contains run_code. |
| [contact_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/contact_tools.py) | `165` | — | `tool_import_contacts()`, `tool_manage_contacts()`, `tool_resolve_contact()` | Contact Management & Mobile Import Tools Plugin for JARVIS. Exposes tools to: - Import mobile contacts (.vcf vCard files |
| [custom_command_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/custom_command_tools.py) | `80` | — | `tool_custom_command_add()`, `tool_custom_command_list()`, `tool_custom_command_delete()` | Registers custom command management tools in the tool registry. |
| [doc_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/doc_tools.py) | `701` | — | `_get_workspace_dir()`, `set_cell_background()`, `set_cell_left_border()` | Automated Executive Document Creator for Microsoft Word (.docx), PDF (.pdf), HTML (.html), and Markdown (.md). Supports  |
| [excel_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/excel_tools.py) | `314` | — | `_get_workspace_dir()`, `create_excel_sheet()`, `analyze_project_to_excel()` | Automated Excel Spreadsheet Generation & Codebase Analysis Suite. Uses openpyxl for building styled, multi-tab .xlsx wor |
| [export_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/export_tools.py) | `29` | — | `tool_export_chat()` | Registers chat log and working memory export tools in the tool registry. |
| [file_import_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/file_import_tools.py) | `34` | — | `tool_import_file_to_knowledge()` | Universal File Ingestion Tools Plugin for JARVIS. Exposes tools to import files (.txt, .pdf, .docx, .md, .csv, .xlsx, .v |
| [file_processor_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/file_processor_tools.py) | `27` | — | `tool_process_universal_file()` | Core subsystem module |
| [file_search_semantic.py](file:///d:\BRJARVIS\Br-Jarvis/tools/file_search_semantic.py) | `72` | — | `semantic_file_search()`, `file_search_semantic_action()` | Fast local semantic file search tool. Matches natural language queries against workspace filenames, extensions, and path |
| [file_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/file_tools.py) | `64` | — | `tool_file_read()`, `tool_file_write()`, `tool_file_list()` | File tools plugin for JARVIS MK37. Contains file_read, file_write, and file_list. |
| [files.py](file:///d:\BRJARVIS\Br-Jarvis/tools/files.py) | `35` | `FileManager` | — | Core subsystem module |
| [git_repo_tool.py](file:///d:\BRJARVIS\Br-Jarvis/tools/git_repo_tool.py) | `116` | — | `_run_git()`, `git_repo_mgr()` | Provides automated Git repository status inspection, diff generation, branch creation & switching, commit staging, tag l |
| [gmail_auth_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/gmail_auth_tools.py) | `78` | — | `tool_gmail_login()`, `tool_get_gmail_auth_status()`, `tool_gmail_logout()` | Gmail Authentication Tools Plugin for JARVIS. Exposes tools for Gmail sign-in, authentication status checking, and accou |
| [image_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/image_tools.py) | `62` | — | `tool_generate_image()`, `tool_edit_image()` | Registers AI image generation and editing tools in the JARVIS tool registry. |
| [legacy_actions_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/legacy_actions_tools.py) | `249` | — | `tool_open_app()`, `tool_game_updater()`, `tool_computer_settings()` | Plugin registering legacy action controllers from the actions/ folder. Unified integration for both ReAct loop and Agent |
| [live_os_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/live_os_tools.py) | `108` | — | `_get_live_os_control()`, `_get_computer_control()`, `tool_live_os_control()` | Live OS Vision Control tools plugin for JARVIS MK37. Exposes autonomous screen perception, fast reaction loop, and visua |
| [mcp_connector.py](file:///d:\BRJARVIS\Br-Jarvis/tools/mcp_connector.py) | `66` | `MCPConnector` | `mcp_call_tool_action()` | Core subsystem module |
| [memory_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/memory_tools.py) | `140` | — | `tool_memory_save()`, `tool_memory_delete()`, `tool_memory_search()` | Memory control tools plugin for JARVIS MK37. Exposes storage capabilities via the memory package. |
| [pc_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/pc_tools.py) | `432` | — | `_get_computer_control()`, `tool_cursor_move()`, `tool_cursor_click()` | PC and OS control tools plugin for JARVIS MK37. Exposes mouse/keyboard/screen automation via actions.computer_control. |
| [process_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/process_tools.py) | `93` | — | `get_system_diagnostics()`, `kill_process()` | System Diagnostics, Process Manager, and Telemetry Inspection Suite. |
| [qa_testing_tool.py](file:///d:\BRJARVIS\Br-Jarvis/tools/qa_testing_tool.py) | `300` | — | `qa_run_browser_test()`, `qa_assert_page_state()`, `qa_generate_report()` | Autonomous Web QA & Software Testing Engine. Allows JARVIS to run background browser tests, validate DOM assertions, rec |
| [rag_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/rag_tools.py) | `113` | — | `tool_rag_ingest()`, `tool_rag_ingest_webpage()`, `tool_rag_query()` | Registers LocalLibrary RAG tools in the JARVIS tool registry. Enables document ingestion, querying, and RAG-augmented ch |
| [recall_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/recall_tools.py) | `41` | — | `tool_remember_that()` | Core subsystem module |
| [redteam_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/redteam_tools.py) | `231` | — | `_get_scope_enforcer()`, `_get_recon_engine()`, `_get_vuln_scanner()` | Red team security tools plugin for JARVIS MK37. Exposes scoped OSINT, port scanning, header audits, and report generatio |
| [registry.py](file:///d:\BRJARVIS\Br-Jarvis/tools/registry.py) | `549` | — | `register_tool()`, `_get_worker_pool()`, `_run_async()` | Universal tool registry and executor for JARVIS MK37. Uses a decorator-based plugin system to register and execute tools |
| [reminder_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/reminder_tools.py) | `24` | — | `tool_schedule_reminder()` | Core subsystem module |
| [sandbox.py](file:///d:\BRJARVIS\Br-Jarvis/tools/sandbox.py) | `91` | `CodeSandbox` | — | Code sandbox for JARVIS MK37. Executes code in a subprocess with timeout protection. Cross-platform: Windows, Linux, mac |
| [scratchpad_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/scratchpad_tools.py) | `104` | — | `tool_scratchpad_write()`, `tool_scratchpad_read()`, `tool_scratchpad_eval()` | Exposes dynamic scratchpad workspace operations as tools. |
| [skills_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/skills_tools.py) | `63` | — | `tool_run_skill()`, `tool_list_skills()` | Skills management tools plugin for JARVIS MK37. Allows querying and running built-in and user custom skills. |
| [smart_email_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/smart_email_tools.py) | `117` | — | `tool_send_email()`, `tool_schedule_email()`, `tool_manage_email_contacts()` | Smart Email Tools Plugin for JARVIS. Exposes tools for composing and sending emails to any recipient or contact, schedul |
| [system_diagnostic_tool.py](file:///d:\BRJARVIS\Br-Jarvis/tools/system_diagnostic_tool.py) | `102` | — | `system_diagnostic()` | Provides real-time system resource monitoring, memory/CPU pressure auditing, disk usage analysis, and network port inspe |
| [system_health.py](file:///d:\BRJARVIS\Br-Jarvis/tools/system_health.py) | `51` | — | `get_system_health()`, `system_health_action()` | System Health & Telemetry tool for JARVIS. Monitors CPU load, RAM memory usage, process count, disk storage, and battery |
| [system_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/system_tools.py) | `183` | — | `tool_cli_controller()`, `tool_system_monitor()`, `tool_screen_share_start()` | System, CLI controller, and screen sharing tools plugin for JARVIS MK37. |
| [tool_runtime.py](file:///d:\BRJARVIS\Br-Jarvis/tools/tool_runtime.py) | `179` | `ToolDefinition`, `ToolRuntimeEngine` | `get_tool_runtime()` | Core subsystem module |
| [transcription_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/transcription_tools.py) | `58` | — | `tool_transcribe_file()`, `tool_transcribe_batch()` | Registers offline audio/video transcription tools in the JARVIS tool registry. |
| [video_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/video_tools.py) | `51` | — | `tool_generate_video()`, `tool_list_generated_videos()` | Registers AI video generation tools in the JARVIS tool registry. |
| [web.py](file:///d:\BRJARVIS\Br-Jarvis/tools/web.py) | `182` | — | `_clean_text()` | Universal high-resilience web search & page extractor for BR-JARVIS. Combines DuckDuckGo, Wikipedia API, Gemini Search G |
| [web_app_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/web_app_tools.py) | `80` | — | `gmail_send()`, `gmail_reply()`, `ms365_control()` | Registered tool wrappers for Gmail and Microsoft 365 / Office Online interactions. |
| [web_extractor.py](file:///d:\BRJARVIS\Br-Jarvis/tools/web_extractor.py) | `61` | — | `extract_web_content()`, `web_extractor_action()` | High-speed HTML parsing and web content extraction tool. Fetches web pages, strips HTML tags, extracts main article cont |
| [web_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/web_tools.py) | `62` | — | `tool_web_search()`, `tool_fetch_page()`, `tool_fetch_raw()` | Web tools plugin for JARVIS MK37. Contains web_search, fetch_page, and fetch_raw. |
| [whatsapp_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/whatsapp_tools.py) | `111` | — | `tool_send_whatsapp()`, `tool_schedule_whatsapp_message()`, `tool_manage_whatsapp_contacts()` | WhatsApp Automation Tools Plugin for JARVIS. Exposes tools for sending instant WhatsApp messages to contacts or phone nu |
| [window_manager.py](file:///d:\BRJARVIS\Br-Jarvis/tools/window_manager.py) | `145` | — | `list_desktop_windows()`, `focus_window_by_title()`, `control_window_state()` | Native Win32 window & process management tool. Allows JARVIS to list open windows, bring applications to focus, inspect  |
| [workspace_tools.py](file:///d:\BRJARVIS\Br-Jarvis/tools/workspace_tools.py) | `100` | — | `open_workspace_file()`, `get_workspace_timeline()`, `init_project_workspace()` | Tools for interacting with the BR JARVIS AI OS Workspace (BR_WORKSPACE/). |

### 3.26 Subsystem: `vision/`
**Description**: 7-Tier Hybrid Vision Subsystem (CDP Browser DOM Bridge, Win32 Accessibility, Tesseract OCR)
**Total Modules**: 8

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/vision/__init__.py) | `18` | — | — | Core subsystem module |
| [accessibility.py](file:///d:\BRJARVIS\Br-Jarvis/vision/accessibility.py) | `105` | `AccessibilityBridge` | `get_accessibility_bridge()` | Core subsystem module |
| [dom_bridge.py](file:///d:\BRJARVIS\Br-Jarvis/vision/dom_bridge.py) | `118` | `CDPBridge` | `get_cdp_bridge()` | Core subsystem module |
| [engine.py](file:///d:\BRJARVIS\Br-Jarvis/vision/engine.py) | `81` | `VisionEngine` | `get_vision_engine()` | Core subsystem module |
| [hybrid_pipeline.py](file:///d:\BRJARVIS\Br-Jarvis/vision/hybrid_pipeline.py) | `68` | `HybridVisionPipeline` | `get_hybrid_pipeline()` | Core subsystem module |
| [ocr_engine.py](file:///d:\BRJARVIS\Br-Jarvis/vision/ocr_engine.py) | `111` | `OCREngine` | — | Core subsystem module |
| [screen_analyst.py](file:///d:\BRJARVIS\Br-Jarvis/vision/screen_analyst.py) | `91` | `ScreenAnalyst` | — | Core subsystem module |
| [types.py](file:///d:\BRJARVIS\Br-Jarvis/vision/types.py) | `125` | `ElementType`, `UIRole`, `ScreenBoundingBox`, `DetectedUIElement`, `SemanticUINode`, `SemanticUIGraph`, `ScreenAnalysisReport` | — | Core subsystem module |

### 3.27 Subsystem: `voice/`
**Description**: Silero VAD, Local Whisper STT, Neural TTS, Voice Prompt Refinement & Audio Pipeline
**Total Modules**: 15

| File Path | Line Count | Primary Classes | Key Functions | Module Role & Description |
|---|---|---|---|---|
| [__init__.py](file:///d:\BRJARVIS\Br-Jarvis/voice/__init__.py) | `16` | — | — | Voice package re-exporting TTS, STT, and Assistant engines. |
| [assistant.py](file:///d:\BRJARVIS\Br-Jarvis/voice/assistant.py) | `701` | `BRVoiceAssistant` | — | Main hands-free voice control coordinator for JARVIS MK37. Integrates Speech Recognition, Wake Word Detection, and ReAct |
| [audio_processor.py](file:///d:\BRJARVIS\Br-Jarvis/voice/audio_processor.py) | `69` | `AudioProcessor` | — | Provides Voice Activity Detection (VAD), RMS audio noise floor estimation, auto-gain adjustment, and silence filtering f |
| [gemini_live.py](file:///d:\BRJARVIS\Br-Jarvis/voice/gemini_live.py) | `185` | `GeminiLiveVoiceLoop` | — | Continuous duplex hands-free voice controller matching the Gemini Live experience. Features: - Continuous multi-turn han |
| [gemini_stt.py](file:///d:\BRJARVIS\Br-Jarvis/voice/gemini_stt.py) | `120` | — | `get_listen_api_key()`, `transcribe_audio_online()` | Dedicated Online Speech-to-Text (STT) Engine for BR JARVIS. Uses GEMINI_LISTEN_API_KEY strictly for audio transcription  |
| [multilingual.py](file:///d:\BRJARVIS\Br-Jarvis/voice/multilingual.py) | `172` | — | `get_language()`, `set_language()`, `get_google_stt_code()` | Provides 90+ language support for speech recognition. Maps ISO-639-1 codes to display names and configures STT engines a |
| [prompt_refiner.py](file:///d:\BRJARVIS\Br-Jarvis/voice/prompt_refiner.py) | `147` | `VoicePromptRefiner` | `refine_voice_prompt()` | Voice Prompt Refinement Engine for BR JARVIS. Cleans raw acoustic speech input by stripping speech hesitation fillers, a |
| [ring_buffer.py](file:///d:\BRJARVIS\Br-Jarvis/voice/ring_buffer.py) | `55` | `AudioRingBuffer` | — | High-performance thread-safe rolling PCM audio ring buffer. Maintains a 500ms pre-roll audio queue (16kHz 16-bit mono PC |
| [shortcuts.py](file:///d:\BRJARVIS\Br-Jarvis/voice/shortcuts.py) | `66` | `VoiceShortcutRegistry` | `match_voice_shortcut()` | Provides fast-path matching for instant voice command execution without passing through full ReAct loop. |
| [silero_vad.py](file:///d:\BRJARVIS\Br-Jarvis/voice/silero_vad.py) | `156` | `SileroVAD` | — | Enterprise-grade Voice Activity Detector powered by Silero VAD (ONNX/PyTorch). Processes 30ms audio PCM chunks (512 samp |
| [sound_effects.py](file:///d:\BRJARVIS\Br-Jarvis/voice/sound_effects.py) | `75` | — | `_run_async_sound()`, `play_activation_beep()`, `play_deep_listening_bass()` | Generates futuristic acoustic audio cues: 1. High-frequency activation chime (1046 Hz -> 1318 Hz) 2. Deep resonant sub-b |
| [stt.py](file:///d:\BRJARVIS\Br-Jarvis/voice/stt.py) | `232` | `SounddeviceMicrophone` | — | Speech recognition source adapters. Bypasses PyAudio dependency by implementing a custom sounddevice-based AudioSource c |
| [tts.py](file:///d:\BRJARVIS\Br-Jarvis/voice/tts.py) | `599` | `MCIPlayer`, `NeuralTTS` | `resolve_output_device()`, `_is_bing_reachable()`, `clean_for_speech()` | Sentence-level pipelined streaming TTS engine with zero sentence pauses, instant <200ms audio startup, parallel pre-fetc |
| [tts_queue.py](file:///d:\BRJARVIS\Br-Jarvis/voice/tts_queue.py) | `105` | `SpeechPriority`, `SpeechItem`, `TTSQueueManager` | — | Thread-safe prioritized speech queue for TTS engines supporting barge-in interrupts, cancellation, and priority dispatch |
| [whisper_local.py](file:///d:\BRJARVIS\Br-Jarvis/voice/whisper_local.py) | `446` | — | `_get_engine()`, `_cuda_available()`, `is_available()` | Offline speech-to-text using OpenAI Whisper running locally. Supports faster-whisper (preferred) or openai-whisper as ba |

---

## 4. Deep Architectural Subsystem Breakdown

### 4.1 ReAct Reasoning & Step Planner Subsystem (`agent/`, `orchestrator/`)
The ReAct loop operates within `orchestrator/core.py` (`JarvisOrchestrator`). It receives structured goals decomposed by `agent/step_planner.py` (`StepPlanner`).
Key characteristics:
- **Adaptive Budgeting**: Starts with an initial window of 5–35 steps. As progress velocity is confirmed by tool outputs, `+5` extensions are granted up to a maximum hard ceiling of 60 steps.
- **Scratchpad Integration**: Transient Python/PowerShell/Bash scripts are evaluated inside `./scratch/` via `agent/scratchpad.py` without mutating system code.
- **Context Reference Resolution**: Automatically resolves ambiguous pronouns ("open it", "search that") by analyzing the last 5 turns in `memory/working.py`.

### 4.2 Meta-Cognition & Speculative Core Subsystem (`reasoning/`)
- `reasoning/meta_cognition.py` (`MetaCognitionEngine`): Evaluates target prompt complexity, calculates pre-execution risk scores ($0.0 \text{ to } 1.0$), and enforces safety gates.
- `reasoning/speculative.py` & `orchestrator/speculative.py` (`SpeculativeEngine`): Generates speculative draft action trajectories in parallel, verifying steps concurrently to reduce total end-to-end execution latency.
- `reasoning/cognitive_loop.py`: Implements an Observe -> Think -> Critic -> Improve -> Retry cycle with critique validation.

### 4.3 5-Tier Memory Architecture & Knowledge Representation (`memory/`)
BR JARVIS uses a unified 5-tier memory subsystem managed by `memory/unified_memory.py` (`UnifiedMemoryEngine`):
1. **Working Memory** (`memory/working.py`): In-memory sliding context window for current conversation session.
2. **Persistent Store** (`memory/persistent_store.py`): SQLite WAL database holding long-term facts, key-value configurations, and historical logs.
3. **Vector RAG Store** (`memory/vector_store.py`): ChromaDB vector embeddings for semantic document and code retrieval.
4. **Temporal Knowledge Graph 2.0** (`memory/temporal_kg.py`): Time-stamped relational edges $(e_1, r, e_2, t_{\text{start}}, t_{\text{end}})$ supporting temporal query snapshots (`query_as_of()`).
5. **Experience Replay DB** (`memory/experience_replay.py`): Trajectory SQLite database tracking execution steps for past task similarity retrieval.
6. **Ebbinghaus Memory Decay Engine** (`memory/decay.py`): Classifies memories into RETAIN, ARCHIVE, or PRUNE based on access frequency and exponential retention curves.

### 4.4 Real-Time Voice & Acoustic Pipeline (`voice/`)
- `voice/silero_vad.py` (`SileroVAD`): ONNX-accelerated Voice Activity Detection segmenting audio chunks with <10ms latency.
- `voice/whisper_local.py` (`WhisperLocalSTT`): In-memory audio byte streaming with RMS silence gating and hallucination filtering.
- `voice/prompt_refiner.py` (`VoicePromptRefiner`): Vocal filler stripper (`um`, `uh`, `like`), hesitation cleaner, and custom vocabulary mapper.
- `voice/tts.py` & `voice/tts_queue.py`: Multi-backend Neural TTS (Edge-TTS / pyttsx3) with non-blocking audio queue.

### 4.5 7-Tier Hybrid Vision Subsystem (`vision/`)
Unified visual perception graph (`SemanticUIGraph`) combining multiple detection tiers:
- **Tier 1 (Win32 Accessibility)**: Direct UI Automation accessibility element trees (`vision/accessibility.py`).
- **Tier 2 (Browser DOM Bridge)**: Chrome/Edge Chrome DevTools Protocol (CDP) DOM bridge (`vision/dom_bridge.py`).
- **Tier 3 (OCR Engine)**: Fast local Tesseract OCR bounding box extractions (`vision/ocr_engine.py`).
- **Tier 4 (Hybrid Pipeline)**: Fuses DOM, Accessibility, and OCR elements into a single queryable visual tree (`vision/hybrid_pipeline.py`).

### 4.6 Computer Operator & OS Native Controls (`computer/`, `actions/`)
- `computer/operator.py` (`ComputerOperator`): Performs low-level Win32 mouse/keyboard actions, window activation, and keypress macros.
- `actions/live_os_control.py` (`LiveOSController`): Autonomous vision control loop performing screenshot -> LLM spatial grounding -> coordinate click.
- `native/jarvis_native.c`: C native DLL bridge for ultra-low latency Win32 process and window management.

### 4.7 Security Governance & Immutable Guardian Core (`guardian/`, `permissions.py`)
- `guardian/core.py` (`GuardianCore`): Intercepts all tool execution requests against path policies and safety matrices.
- `guardian/kill_switch.py`: Instant emergency kill switch to stop out-of-control tasks.
- `guardian/snapshot.py` & `guardian/rollback.py`: File system state snapshotting and 1-click system rollback.
- `guardian/audit_log.py`: Cryptographic SHA256 append-only ledger of system operations.
- `permissions.py`: Global security policy definition and path whitelist enforcer.

---

## 5. Storage & Database Schemas

### 5.1 Temporal Knowledge Graph 2.0 (`memory/temporal_kg.py`)
Stores temporal edges: $(e_1, r, e_2, t_{\text{start}}, t_{\text{end}})$
```sql
CREATE TABLE IF NOT EXISTS temporal_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    relation TEXT NOT NULL,
    target TEXT NOT NULL,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Trajectory Experience Replay (`memory/experience_replay.py`)
```sql
CREATE TABLE IF NOT EXISTS trajectories (
    trajectory_id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    success INTEGER NOT NULL,
    score REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.3 Durable Task DAG Engine (`workflow/task_dag.py`)
```sql
CREATE TABLE IF NOT EXISTS task_dag_nodes (
    task_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    error TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, node_id)
);
```

---

## 6. End-to-End Execution Flow

```
1. User Vocal Input / Text Command
   ├── VAD Acoustic Gating (voice/silero_vad.py)
   ├── Zero-Disk Whisper Transcription (voice/whisper_local.py)
   └── Voice Prompt Refinement (voice/prompt_refiner.py)
2. Zero-Token Intent Engine (core/intent_engine.py)
   ├── IF Matched: Execute immediately (0ms, 0 tokens) -> Speech Output (voice/tts.py)
   └── IF Complex: Forward to Conscious Step Planner (agent/step_planner.py)
3. Meta-Cognition & Speculative Planning
   ├── Risk Assessment & Confidence Scoring (reasoning/meta_cognition.py)
   ├── Draft Step Speculation (reasoning/speculative.py)
   └── Execution Path Budgeting (agent/step_planner.py)
4. ReAct Reasoning Loop (orchestrator/core.py)
   ├── Dynamic Multi-Objective Backend Selection (router/core.py)
   ├── Context Reference Resolution (context/engine.py)
   ├── Tool Execution (tools/registry.py)
   ├── 7-Tier Vision Feedback (vision/engine.py)
   └── Antigravity Scratchpad Evaluation (agent/scratchpad.py)
5. State Update & Knowledge Memory
   ├── Temporal Knowledge Graph Mutation (memory/temporal_kg.py)
   ├── Experience Replay Storage (memory/experience_replay.py)
   └── Ebbinghaus Memory Decay Classification (memory/decay.py)
6. Safety & Guardian Validation
   ├── SHA256 Hash Integrity Verification (guardian/core.py)
   ├── Path & Command Policy Enforcer (guardian/core.py)
   └── GUI / Voice Response Output to User
```

---

## 7. Recent Structural Audits & Deep Fixes (August 2026)

### 7.1 Missing Internal Modules & Shims Resolved
- **Package Initializers**: Created missing `__init__.py` files for `desktop_ui/`, `native/`, `evolution/`, `workspace/`, and `workflow/` packages.
- **Workflow Task DAG**: Created `workflow/task_dag.py` containing `DAGNodeState` and `PersistentTaskDAG` to support the asynchronous task scheduler.
- **UI Legacy Shim**: Added `ui.py` as a redirection shim pointing to `ui_mark.py` to maintain compatibility with legacy imports.

### 7.2 Duplicate Function Pruning
- **live_os_control.py**: Removed a secondary duplicate of `_save_action_visualization()` (lines 469-489) that conflicted with the primary implementation.
- **server.py**: Removed a duplicate implementation of `run_generator_in_thread()` (lines 184-208) to consolidate sync-to-async thread loop handling.

### 7.3 Deadlocks & Integrity Failures Fixed
- **Reentrant Lock Fix**: Resolved a critical deadlock in `memory/memory_manager.py` by converting `_lock = Lock()` to `_lock = RLock()`. This prevents self-deadlocks when `save_session_summary()` (which holds the lock) invokes `load_memory()` (which attempts to re-acquire it).
- **Guardian Rehash**: Updated `.guardian_hashes.json` using `GuardianCore().rehash_integrity()` to reflect authorized modifications in `guardian/kill_switch.py` (which converted relative paused flags to absolute parent-based paths).
- **Unicode Terminal Safety**: Replaced unicode emojis (like ⚡) in test suite console print statements within `tests/test_master_suite.py` to prevent `UnicodeEncodeError` crashes on default Windows terminals.

### 7.4 Native Compilation & Smoke Check Resilience
- **Native C Source Path Fix**: Corrected path resolution in [setup_native.py](file:///d:/BRJARVIS/Br-Jarvis/scripts/setup_native.py#L26) from `.parent` to `.parent.parent` so `NATIVE_DIR` correctly points to `native/` in the project root instead of `scripts/native/`, which was missing and causing C compilation checks to warn on launch.
- **Dynamic setup_native Import**: Modified [native_bridge.py](file:///d:/BRJARVIS/Br-Jarvis/core/native_bridge.py#L44-L50) to gracefully resolve `setup_native` from the `scripts` module with backward compatibility fallbacks.
- **Default Scope Safeguard**: Created a default [current_scope.json](file:///d:/BRJARVIS/Br-Jarvis/current_scope.json) file to prevent the system-wide smoke-test suite (`smoke_startup.py`) from failing due to missing non-committed gitignored configuration files, bringing sanity checks to 10/10 green.

### 7.5 Platform Path Configuration Audits & Standardization
- **Auto-Startup Config Path Fix**: Updated directory resolution in [install_startup.py](file:///d:/BRJARVIS/Br-Jarvis/scripts/install_startup.py#L24) from `.parent` to `.parent.parent` to point to the repository root directory instead of the `scripts/` directory, preventing invalid executable path assignments in auto-generated desktop entries and launch agents.
- **Skill Library Dynamic Lookup**: Changed `LIBRARY_DIR` in [reformat_skills_library.py](file:///d:/BRJARVIS/Br-Jarvis/scripts/reformat_skills_library.py#L12) to dynamically compute location relative to the project root instead of hardcoding absolute paths.
- **Regression Test Path Portability**: Updated path validation checks in [test_regression_fixes.py](file:///d:/BRJARVIS/Br-Jarvis/tests/test_regression_fixes.py#L47) to dynamically resolve paths using `Path().resolve()` instead of hardcoding a Windows D-drive path string.
- **Headless Display & CLI Fallback**: Added display presence diagnostics (`is_gui_available`) using sandbox subprocesses and defined [HeadlessJarvisUI](file:///d:/BRJARVIS/Br-Jarvis/ui_mark.py#L3505) as an interactive CLI fallback wrapper in [ui_mark.py](file:///d:/BRJARVIS/Br-Jarvis/ui_mark.py#L3609) to prevent application execution failures in headless terminal environments.
- **Launcher Subprocess Isolation**: Updated [start.py](file:///d:/BRJARVIS/Br-Jarvis/start.py#L631) in dev/source mode to launch `ui_mark.py` as an isolated subprocess rather than loading `run_voice_ui` directly inside the launcher thread. This completely resolves PyQt/PySide event loop startup crashes resulting from parent thread signal conflicts.
- **Sub-window Close Protection**: Override [closeEvent](file:///d:/BRJARVIS/Br-Jarvis/ui_mark.py#L3470) in `MainWindow` to trigger `QApplication.quit()` and set `setQuitOnLastWindowClosed(False)` in [ui_mark.py](file:///d:/BRJARVIS/Br-Jarvis/ui_mark.py#L3616). This prevents the main Qt event loop from automatically terminating when temporary sub-windows or overlays are closed.
- **Passive Voice Assistant Daemon**: Modified [HeadlessJarvisUI.mainloop](file:///d:/BRJARVIS/Br-Jarvis/ui_mark.py#L3597) to intercept `EOFError` (which is raised when standard input is unavailable or closed) and fall back to a passive hands-free sleep loop. This prevents the console assistant thread from automatically exiting and keeps the offline voice listener active.
- **Modular UI Refactoring (Option B)**: Refactored the monolithic 3,775-line `ui_mark.py` file into a clean Python package under the [ui/](file:///d:/BRJARVIS/Br-Jarvis/ui/) directory. Exposes all public widgets, palettes, overlays, windows, and setup interfaces via a facade in [ui_mark.py](file:///d:/BRJARVIS/Br-Jarvis/ui_mark.py), guaranteeing complete backward compatibility with all test suites, launch scripts, and core subsystems.
- **Metric Monitoring Instance Bind**: Imported [_metrics](file:///d:/BRJARVIS/Br-Jarvis/ui/widgets.py#L226) from `ui.widgets` inside [ui/main_window.py](file:///d:/BRJARVIS/Br-Jarvis/ui/main_window.py#L105) to resolve NameError crashes during window metric update ticks (`_update_metrics`).