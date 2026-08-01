# 🌌 BR JARVIS — Master Architecture Record & Full Project Specification

> **System Identity**: BR JARVIS (Project BR / JARVIS MK38)  
> **Version**: MK38.2.0 — Meta-Cognition, Speculative Core & World Intelligence Subsystems  
> **Target Platform**: Windows 11 / Linux / macOS  
> **Last Updated**: 2026-07-25  
> **Test Coverage**: 110 automated Pytest unit & integration test suites passing cleanly (100% green)  

---

## 1. Executive Summary & Vision

**BR JARVIS** is a local-first, multi-modal cognitive AI operating system built for autonomous PC control, hands-free voice interaction, multi-backend LLM routing, screen vision, self-improvement, and immutable safety governance.

It is not a simple chatbot wrapper — it is a full **AI Operating System** with 18 specialized subsystems working together in an asynchronous, event-driven architecture.

### 🎯 Core Architectural Principles

| Principle | Implementation | Status |
|---|---|---|
| **Meta-Cognition Engine** | `reasoning/meta_cognition.py` — Pre-execution risk assessment & confidence scoring ($0.0 \text{ to } 1.0$) | ✅ Production |
| **Speculative Execution Engine** | `reasoning/speculative.py` & `orchestrator/speculative.py` — Speculative draft step generator & parallel validator | ✅ Production |
| **Trajectory Experience Replay DB** | `memory/experience_replay.py` — SQLite WAL trajectory store for similarity retrieval & playback | ✅ Production |
| **Temporal Knowledge Graph 2.0** | `memory/temporal_kg.py` — Time-stamped relational edges $(e_1, r, e_2, t_{\text{start}}, t_{\text{end}})$ & `query_as_of` snapshots | ✅ Production |
| **Semantic Workspace Code Graph** | `workspace/code_graph.py` — Zero-token AST code symbol definition & reference resolution | ✅ Production |
| **Closed-Loop Cognitive Cycle** | `reasoning/cognitive_loop.py` & `agent/critic_agent.py` — Observe -> Think -> Critic -> Improve -> Retry cycle | ✅ Production |
| **Relational Knowledge Graph World Model** | `memory/knowledge_graph.py` — NetworkX relational entity graph connecting workspace resources | ✅ Production |
| **Persistent Task DAG & Crash Resume** | `workflow/task_dag.py` — SQLite WAL atomic step checkpointing (`checkpoint()`, `resume()`) | ✅ Production |
| **Multi-Objective Model Router** | `router.py` — `select_multi_objective_backend()` balancing Quality, Cost, and Latency | ✅ Production |
| **Memory Decay & Forgetting Engine** | `memory/decay.py` — Ebbinghaus retention decay engine classifying memories into `RETAIN`, `ARCHIVE`, `PRUNE` | ✅ Production |
| **Ultra-Fast Silero VAD Voice Engine** | `voice/silero_vad.py` — ONNX Silero VAD segmenter for acoustic speech chunking (<10ms latency) | ✅ Production |
| **Zero-Disk Whisper Audio Streaming** | `voice/whisper_local.py` — In-memory audio byte streaming with RMS silence gating & hallucination filter | ✅ Production |
| **CDP DOM Bridge Vision Tier** | `vision/dom_bridge.py` — Real-time Chrome/Edge browser accessibility DOM inspection bridge | ✅ Production |
| **Zero-Token Instant Execution** | `core/intent_engine.py` — 50+ deterministic matchers executing system commands in 0ms, 0 LLM tokens | ✅ Production |
| **Voice Prompt Refinement Engine** | `voice/prompt_refiner.py` — Vocal hesitation cleaner, filler stripper (`um`, `uh`, `like`), and vocab mapper | ✅ Production |
| **Conscious Step Planner & Adaptive Budget** | `agent/step_planner.py` — Goal decomposition & progress velocity evaluator (+5 step extensions up to 60 ceiling) | ✅ Production |
| **Antigravity Scratchpad Engine** | `agent/scratchpad.py` & `tools/scratchpad_tools.py` — Isolated `./scratch/` workspace & multi-lang `scratchpad_eval` | ✅ Production |
| **Autonomous Planning Mode & GFM Artifacts** | `agent/planning_mode.py` & `agent/artifacts.py` — Dynamic complexity classifier, `implementation_plan.md` & `walkthrough.md` | ✅ Production |
| **Trajectory Transcripts Logging** | `agent/transcript_logger.py` — JSON Lines trajectory logger (`transcript.jsonl`) | ✅ Production |
| **Multi-Task & Sub-Agent UI Dashboard** | `ui.py` — Control Center tab displaying Task Cards with status badges (`RUNNING`, `QUEUED`, `COMPLETED`, `FAILED`), progress bars & canvas HUD | ✅ Production |
| **Multi-Backend Clipboard Engine** | `actions/clipboard_utils.py` — 5-layer prioritized fallback (`pyperclip` -> Win32 `ctypes` -> `tkinter` -> PowerShell -> CLI) | ✅ Production |
| **Context-Aware Pronoun Resolution** | `orchestrator._resolve_context_references()` — resolves "open it in brave" using conversation history | ✅ Production |
| **Multi-Backend LLM Routing** | `router.py` — 7 backends: Gemini (including 3.6 Flash & Agent models), Claude, GPT, DeepSeek, NVIDIA, Ollama, Mistral | ✅ Production |
| **Immutable Guardian Core** | `guardian/` — kill-switch, snapshot, rollback, audit ledger | ✅ Production |
| **Autonomous Self-Upgrade** | `evolution/` — blast-radius classifier, sandbox testing, auto-deploy | ✅ Production |
| **Multi-Tier Memory** | `memory/` — 5 storage tiers: Working, SQLite, ChromaDB, LessonStore, FNV-1a cache | ✅ Production |
| **Live OS Vision Control** | `actions/live_os_control.py` — screenshot→LLM→action loop with visual grounding trace | ✅ Production |
| **Deep Desktop Automation** | `computer/`, `actions/computer_control.py` — Win32, PyAutoGUI, accessibility trees | ✅ Production |
| **7-Tier Vision Pipeline** | `vision/` — screen capture, OCR, DOM bridge, accessibility, hybrid pipeline | ✅ Production |

---

## 2. System Architecture Topology

```mermaid
graph TD
    User([👤 User Voice / Text]) --> VoiceRefiner[VoicePromptRefiner<br/>voice/prompt_refiner.py]
    VoiceRefiner --> Interface

    subgraph Interface["🖥️ Interface Layer"]
        VoiceUI[Voice GUI<br/>floating_voice_ui.py]
        TKUI[Tkinter Desktop UI<br/>ui.py & Multi-Task Dashboard]
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

    subgraph Orchestrator["🧠 JarvisOrchestrator<br/>orchestrator.py"]
        StepBudget --> ContextResolver[Context Resolver<br/>_resolve_context_references]
        ContextResolver --> WorkingMemory[Working Memory<br/>memory/working.py]
        WorkingMemory --> ReactLoop[ReAct Loop<br/>Adaptive Step Budget]
    end

    ReActLoop --> ModelRouter[AgentRouter<br/>router.py]

    subgraph LLMBackends["🔀 Multi-LLM Provider Engine"]
        ModelRouter --> Gemini[Gemini 2.5 / 3.5 Flash]
        ModelRouter --> Claude[Claude 3.5 Sonnet]
        ModelRouter --> GPT[GPT-4o / OSS 120B]
        ModelRouter --> DeepSeek[DeepSeek R1]
        ModelRouter --> NVIDIA[NVIDIA NIM Llama3]
        ModelRouter --> Ollama[Local Ollama]
    end

    subgraph ExecutionSubsystems["🔧 Subsystems & Tool Ecosystem"]
        ReActLoop --> ToolRegistry[Tool Registry<br/>tools/registry.py<br/>98 Tools]
        ToolRegistry --> Scratchpad[Scratchpad Engine<br/>agent/scratchpad.py<br/>./scratch/ Workspace]
        ToolRegistry --> LiveOS[Live OS Controller<br/>actions/live_os_control.py]
        ToolRegistry --> CompOp[Computer Operator<br/>computer/operator.py]
        ToolRegistry --> Vision[Vision Engine<br/>vision/engine.py]
        ToolRegistry --> Memory[Multi-Tier Memory<br/>SQLite + ChromaDB + Markdown]
    end
```

---

## 3. Subsystem Architectural Breakdown

### 3.1. Conscious Step Planner & Adaptive Flexible Step Budget (`agent/step_planner.py`)
- Decomposes target goals into conscious sub-steps prior to ReAct execution.
- Evaluates progress velocity during execution; when active tool progress is confirmed, grants `+5` step extensions up to a maximum hard ceiling of 60 steps.

### 3.2. Voice Prompt Refinement Engine (`voice/prompt_refiner.py`)
- Acoustic speech cleaner that strips vocal hesitation fillers (`um`, `uh`, `like`, `you know`).
- Maps domain vocabulary using `config/vocabulary.json` and logs `Spoken Raw` vs `Refined Prompt` in the UI.

### 3.3. Antigravity Scratchpad Workspace (`agent/scratchpad.py` & `tools/scratchpad_tools.py`)
- Isolated workspace at `./scratch/` supporting transient evaluation (`scratchpad_eval`) for Python, Node.js, PowerShell, and Bash with stdout/stderr capture.

### 3.4. Multi-Task Frontend Dashboard (`ui.py`)
- Dedicated **"🚀 Multi-Tasks"** tab rendering glossy **Task Cards**, progress bars, and status badges (`RUNNING`, `QUEUED`, `COMPLETED`, `FAILED`).

### 3.5. 7-Tier Hybrid Vision Subsystem (`vision/`)
- Integrates Tier 1 Windows Accessibility API, Tier 2 CDP Browser DOM Bridge, and Tesseract OCR into a unified `SemanticUIGraph`.

---

## 4. Codebase Directory Topology & Packages

```
Br-Jarvis/
├── actions/             # Desktop, browser, app, and 5-tier clipboard actions (34 files)
├── agent/               # Planner, executor, step planner, scratchpad, artifacts, transcripts
├── backends/            # AI provider adapters (Gemini, Claude, GPT, Ollama, DeepSeek, NVIDIA, Mistral)
├── br_architecture/      # Engineering knowledge base index & specs
├── computer/            # Desktop operator, win32 handles, semantic finder, recovery
├── config/              # Model config, hotkeys, vocabulary settings
├── context/             # Token counter, sliding window, context reference resolver
├── core/                # Bootstrap, DI container, retry, intent engine, error middleware
├── events/              # Pub/Sub EventBus, event types & topics
├── evolution/           # Self-upgrade sandbox, classifier, deployer
├── guardian/            # PathPolicy, integrity hashing, kill switch, rollback
├── history/             # Session store, replay engine, transcript writer
├── memory/              # Working memory, SQLite store, ChromaDB vector RAG, cache
├── multi_agent/         # Sub-agent spawning framework (12 subagent definitions)
├── native/              # C native win32 bridge (jarvis_native.c)
├── plugins/             # Plugin manager, isolation & tool registry bridge
├── reasoning/           # Chain-of-thought engine, plan graph DAG
├── redteam/             # Recon scanner, security auditor, scope manager
├── screen_server/       # Real-time WebSocket screen stream server
├── skills/              # Skill loader & builtins (RAG, Auditor, Writer, Excel)
├── tools/               # Tool registry & 34 tool modules
├── vision/              # Hybrid 7-tier vision engine, OCR, DOM bridge, accessibility
├── voice/               # Whisper STT, Neural TTS, prompt refiner, wake-word assistant
├── web/                 # Glassmorphic Web UI dashboard (HTML/CSS/JS)
├── workflow/            # Durable workflow DAG engine, SQLite persistence
├── floating_voice_ui.py # Gemini Live floating overlay UI
├── main_mk37.py         # Rich TUI CLI launcher
├── orchestrator.py      # Core ReAct reasoning & execution loop
├── permissions.py       # Security policy & permission matrix
├── router.py            # Dynamic multi-backend AI model router
├── server.py            # FastAPI REST & WebSocket server
├── start.py             # System entry point
└── ui.py                # Tkinter Maximum Control Center HUD (72KB monolith)
```
