# ⚡ BR JARVIS — Autonomous Personal AI Operating Runtime

[![CI](https://github.com/bharthraj1412/BrJarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/bharthraj1412/BrJarvis/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-325%2B%20passing-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

> **BR JARVIS** is an autonomous personal AI operating runtime designed for pair programming, system automation, multimodal vision, hands-free voice control, and verifiable task execution.

---

## 🏛️ Canonical Architecture

```mermaid
graph TD
    CLI[CLI REPL Interface] --> Runtime[ApplicationRuntime]
    VoiceUI[Voice & Floating UI] --> Runtime
    WebUI[Web PWA & Mobile Dashboard] --> Runtime
    
    subgraph "Canonical Core"
        Runtime --> Config[ConfigManager]
        Runtime --> EventBus[EventBus & Telemetry]
        Runtime --> Security[SecurityPolicyEngine & Guardian]
        Runtime --> Artifacts[ArtifactLifecycleManager]
    end

    subgraph "Cognitive Execution Engine"
        Runtime --> Cognitive[CognitiveEngine]
        Cognitive --> Intent[Intent & Task Decomposer]
        Intent --> DAG[TaskDAG & Recovery Engine]
        DAG --> Gateway[ModelGateway & Smart Router]
        DAG --> ToolRuntime[ToolRuntime & ToolRegistry]
        DAG --> Verifier[ActionVerifier]
    end

    subgraph "Perception & Memory"
        Runtime --> Memory[UnifiedMemoryManager]
        Runtime --> Voice[VoicePipeline (VAD + STT + Barge-In + TTS)]
        Runtime --> Vision[HierarchicalVision (OCR + DOM + VLM)]
    end
```

---

## 🚀 Quick Start

### 1. Installation
```powershell
git clone https://github.com/bharthraj1412/BrJarvis.git
cd BrJarvis
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the template and configure your API keys:
```powershell
Copy-Item .env.template .env
```

### 3. Launch Sequences
```powershell
# Interactive Launcher Menu
python start.py

# Direct CLI REPL
python start.py cli

# Hands-Free Voice Assistant HUD
python start.py voice

# Frameless Floating Voice Widget
python start.py floating

# Web PWA & Mobile Server
python start.py server

# Subsystem Diagnostic Matrix
python start.py status

# Startup Sanity Verification
python start.py smoke
```

---

## 🛡️ Key Guarantees

1. **Deterministic Postcondition Verification**: JARVIS never fabricates success. Actions (file writes, process spawns, browser URLs, document exports) are verified against environmental state.
2. **Authoritative Artifact Export**: Sandbox files are verified, checked for path traversal, and exported to host before opening in a browser, eliminating `ERR_FILE_NOT_FOUND`.
3. **Quarantined Personal Data**: User contacts and private databases reside in `~/.jarvis/` and are never committed to Git.
4. **Active Barge-In**: Real-time Silero VAD immediately halts TTS playback and clears audio queues when you speak.
5. **Provider-Neutral Gateway**: Supports Gemini, OpenAI, Claude, DeepSeek, Mistral, NVIDIA NIM, and local Ollama with typed diagnostic error classification.

---

## 🧪 Testing & Verification

Run the full automated test suite:
```powershell
pytest tests/unit/ -v
```

Run startup smoke check:
```powershell
python start.py smoke
```

---

## 📜 Documentation Index
- [`docs/operations/MANUAL_WORKS_AND_OPERATIONS_GUIDE.md`](docs/operations/MANUAL_WORKS_AND_OPERATIONS_GUIDE.md) — **Manual Setup, Keys, Audio & Operations Guide.**
- [`docs/FILE_AUDIT.md`](docs/FILE_AUDIT.md) — Comprehensive forensic inventory of every repository file.
- [`docs/MODERNIZATION_LEDGER.md`](docs/MODERNIZATION_LEDGER.md) — Architectural modernization ledger across all 18 phases.
- [`docs/architecture/full-system-map.md`](docs/architecture/full-system-map.md) — Full system subsystem topology and lifecycle.
