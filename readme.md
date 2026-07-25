# 🧠 BR JARVIS — Local-First Autonomous AI Operating System

[![CI](https://github.com/bharthraj1412/BrJarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/bharthraj1412/BrJarvis/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Engine](https://img.shields.io/badge/Engine-Gemini--Native-orange.svg)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/tests-136%2F136%20passing-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

> **BR JARVIS** is not a simple chatbot. It is an **Autonomous Local-First AI Operating System** — a modular, production-grade cognitive platform that understands your computer, reasons about multi-step goals, and executes complex tasks through voice perception, computer vision, Win32 desktop automation, hybrid 10-tier memory, and DAG planning.

---

## 🌟 Key Highlights & Next-Gen Capabilities

* **🎙️ Duplex Voice Perception & DSP Equalizer**: Dual-stage ring-buffered voice system with 500ms pre-roll, Silero VAD v5, high-pass audio filtering ($80\text{ Hz}$), noise gate, acoustic speaker biometric verification, and barge-in speech cancellation.
* **🖱️ Win32 Desktop GUI Operator & Window Manager**: Enumerate active application windows, focus desktop windows, execute mouse/keyboard actions, and auto-recover from PyAutoGUI corner failsafes.
* **⚡ Speculative Multi-Model Router & Prompt Caching**: Parallel model racing gateway with SHA-256 prompt hashing (`PromptCacheManager`), token budget optimization, and speculative fast-path intent classification (`SpeculativeEngine`).
* **📂 Local Semantic File Search & Web Extractor**: Natural language workspace file finder (`file_search_semantic`) and high-speed HTML content extraction tool (`web_extractor`).
* **💻 Real-Time System Health Telemetry**: Live CPU load, RAM memory usage, disk space, process telemetry, and battery state monitoring (`system_health`).
* **🩺 Autonomous User Skills System**: Invocation framework featuring `researcher` (multi-source web research), `code_doctor` (self-healing syntax tree diagnostician), `security_auditor` (secret scanner), and `doc_architect` (Mermaid documentation generator) with dynamic hot-reloading (`SkillHotReloader`).
* **🛡️ Zero-Trust Security Interlocks**: Permission policy engine, sandboxed WASM tool execution runtime, human-in-the-loop interlocks, and emergency stop kill-switches.
* **🧪 100% Verified Automated Test Suite**: 136 green unit & integration test cases verifying core runtime, event bus, vision engine, voice pipeline, and sub-agent execution.

---

## 📊 System Architecture

```mermaid
graph TD
    User([👤 User — Voice / Vision / Text Input]) --> HUD[🖥️ Frameless Glassmorphic HUD & Dual Interface]

    HUD --> Router[🔀 Multi-Backend Router & Speculative Selector<br/>SHA-256 PromptCache + Token Budgeting]
    HUD --> EventBus[📡 EventBus — Pub/Sub + Audit Log]

    Router --> Gemini[Gemini 2.5/3.5 Flash]
    Router --> Ollama[Local Ollama / CTranslate2 — Offline]
    Router --> CloudOthers[GPT-4o / Claude 3.5 Sonnet / Mistral]

    Router --> TaskQueue[⚡ Parallel Task Queue & DAG Planner Engine]
    TaskQueue --> Executor[🚀 Parallel Execution Engine<br/>Emergency Stop + Human Interlocks]

    Executor --> ToolRegistry[🔧 Tool Registry Engine — Sandboxed]
    Executor --> VisionEngine[👁️ Vision Engine<br/>Screen Capture + RapidOCR + Bounding Boxes]
    Executor --> ComputerOp[🖱️ Computer Operator & Win32 Window Manager<br/>Mouse + Keyboard + Window Focus]

    ToolRegistry --> DesktopTools[OS Automation & Window Manager]
    ToolRegistry --> SemanticTools[Semantic File Search + Web Extractor]
    ToolRegistry --> HealthTools[System Health & Telemetry]
    ToolRegistry --> AIModels[Imagen 3 / Veo / Whisper / Silero VAD]

    subgraph Memory & Skills Runtime
        Mem10[💾 10-Tier Hybrid Memory — Vector + Graph RAG + Episodic]
        HotReload[🔥 Skill Hot-Reload Engine — Dynamic .md Discovery]
        Skills[🩺 Active Skills: researcher | code_doctor | security_auditor | doc_architect]
    end

    Executor -.-> Mem10
    TaskQueue -.-> Skills
    HotReload -.-> Skills
```

---

## 🏗️ Production-Grade Subsystems

BR JARVIS is engineered from modular, tested subsystems — each with its own Pydantic v2 models, EventBus telemetry, and Dependency Injection registration:

| # | Subsystem | Module | Key Capabilities |
|---|---|---|---|
| 1 | **Core Runtime & Bootstrap** | `core/` | Pydantic config, DI container, lifecycle management, health monitoring |
| 2 | **Event Bus System** | `events/` | Async pub/sub, wildcard routing, dead letter queue, audit persistence |
| 3 | **Context & Token Budget** | `context/`, `reasoning/prompt_cache.py` | SHA-256 prompt hashing, token accounting, semantic compression |
| 4 | **10-Tier Hybrid Memory** | `memory/` | RAM working buffer, TTL cache, ChromaDB vector RAG, SQLite episodic store |
| 5 | **DAG Planner Engine** | `agent/planner_engine.py` | DAG goal decomposition, risk classification (LOW→CRITICAL), replanning |
| 6 | **Parallel Execution Engine** | `agent/executor_engine.py` | Multi-worker parallel execution, emergency stop, human approval interlocks |
| 7 | **Tool Registry & Sandbox** | `tools/` | Sandboxed tool execution, permission policies, result caching |
| 8 | **Speculative Router & Engine** | `reasoning/speculative_engine.py` | Fast-path intent classification, dynamic speed-quality model routing |
| 9 | **Vision Engine** | `vision/` | Screen capture (mss), FNV-1a frame dedup, OCR text extraction, UI element detection |
| 10 | **Win32 Computer Operator** | `computer/`, `tools/window_manager.py` | Mouse/keyboard control, Win32 window focus, PyAutoGUI failsafe recovery |
| 11 | **Duplex Voice System** | `voice/` | Silero VAD v5, pre-roll ring buffer, audio DSP equalizer, speaker biometrics |
| 12 | **Skill Hot-Reload Platform** | `skills/` | Dynamic `.md` skill discovery (`researcher`, `code_doctor`, `security_auditor`, `doc_architect`) |

---

## ⚡ Quick Start Guide

### 1. Clone Repository & Install Dependencies

```bash
git clone https://github.com/bharthraj1412/BrJarvis.git
cd BrJarvis
pip install -r requirements_mk37.txt
```

### 2. Configure API Key Environment

Set your Google Gemini API key in a `.env` file or environment variable:

```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# Linux / macOS
export GEMINI_API_KEY="your-gemini-api-key-here"
```

### 3. Run BR JARVIS Assistant

Launch the interactive voice & CLI assistant orchestrator:

```bash
python main.py
```

---

## 🧪 Automated Testing & Quality Assurance

Run the comprehensive pytest suite verifying all 136 unit and integration test cases:

```bash
python -m pytest tests/
```

### Test Coverage Highlights:
* **Core & Integration**: `test_core_runtime.py`, `test_event_bus.py`, `test_memory_context.py`
* **Voice Pipeline & DSP**: `test_voice_pipeline.py`, `test_voice_latency.py`, `test_flaw_remediations_v3.py`
* **Vision & Desktop Automation**: `test_vision_operator.py`, `test_computer_operator.py`, `test_nextgen_features.py`
* **Next-Gen Upgrades**: `test_phase2_features.py`, `test_phase3_features.py`, `test_phase4_features.py`, `test_system_upgrades_v4.py`, `test_flaw_remediations_v5.py`

---

## 📜 License & Acknowledgments

Distributed under the **MIT License**. Built with Google Gemini, PySide6, ChromaDB, CTranslate2, Silero VAD, PyAutoGUI, and Python 3.10+.
