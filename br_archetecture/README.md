# 🧠 BR JARVIS — Engineering Knowledge Base Index

Welcome to the **BR JARVIS (Project BR / JARVIS MK37)** Engineering Knowledge Base. This directory serves as the persistent architectural brain, technical documentation, and long-term design memory for the BR JARVIS AI Operating System (Version 37.31.0).

---

## 📁 Knowledge Base Hierarchy

```
br_archetecture/
├── README.md                          # Root Knowledge Base index (This file)
├── fullproject.md                     # Master Full Project Specification & Architecture
├── PROJECT_VISION.md                  # Project BR vision, philosophy & objectives
├── ROADMAP.md                         # Multi-phase development roadmap & milestone status
├── CHANGELOG.md                       # Architectural execution changelog (v37.31.0)
├── full_repository_audit.md           # Deep engineering audit report & bug tracking (BUG-001 to BUG-012)
├── architecture/
│   ├── ARCHITECTURE.md                # System topology, data flow & component graph
│   └── PROJECT_STRUCTURE.md            # Codebase directory mapping (~180 Python files, 30+ packages)
├── planning/
│   ├── FEATURE_MATRIX.md              # Implemented capability status matrix (15 core subsystems)
│   ├── TECHNICAL_DEBT.md              # Refactoring targets & debt audit
│   └── TASKS.md                       # Active task backlog & fix priorities
├── ai/
│   ├── CONTEXT_ENGINE.md              # Context assembly, reference resolution & token compression
│   ├── MEMORY_ENGINE.md               # 5-tier memory architecture (Working, SQLite, Vector RAG, Lessons, Cache)
│   ├── MODEL_ROUTER.md                # Dynamic multi-backend router & failover strategies (7 AI backends)
│   └── TOKEN_OPTIMIZATION.md          # 50+ Zero-token intent engine & native FNV-1a caching
├── computer/
│   └── COMPUTER_OPERATOR.md           # OS computer operator, 5-tier clipboard & visual trace overlay
├── vision/
│   └── VISION_ENGINE.md               # 7-Tier Hybrid Vision Engine (Accessibility, CDP DOM, Tesseract OCR)
├── voice/
│   └── VOICE_ENGINE.md               # Hands-free voice assistant, Silero VAD, Whisper ASR & Neural TTS
├── plugins/
│   └── PLUGIN_SYSTEM.md               # Plugin platform, Antigravity Scratchpad (`./scratch/`) & tool registry
├── core/
│   └── EVENT_SYSTEM.md                # Pub/Sub EventBus, Conscious Step Planner & Telemetry Store
├── security/
│   └── SECURITY.md                    # Guardian Core, PathPolicy bounds checking, redteam audit & secret scan
├── ui_img/
│   ├── AI_OS_REDESIGN_MASTER_SPEC.md  # Maximum Control Center, Multi-Tasks tab & Task Cards spec
│   ├── UI_UX_DESIGN.md                # Tkinter HUD & glassmorphic Web UI specifications
│   └── redesign.md                    # Interface modernization roadmap & UI specs
├── upgrademd/
│   ├── BR_JARVIS_Master_Fix_Prompt.md  # Master system prompt & architecture directives
│   ├── BR_JARVIS_Master_Fix_Prompt_v2.md # Version 2 master system prompt & fix specs
│   ├── BR_JARVIS_UNIFIED_MASTER_PROMPT.md # Unified master prompt specification
│   ├── computervision.md               # Deep computer vision technical report
│   ├── deep-research-report.md         # Autonomous AI OS architecture research report (Part 1)
│   └── deep-research-report (1).md     # Autonomous AI OS architecture research report (Part 2)
└── performance/
    └── BENCHMARKS.md                  # Latency budgets, hardware metrics & test suite benchmarks
```

---

## 🚀 Key Architectural Innovations in MK38 (v38.2.0)

1. **Meta-Cognition Engine & Pre-Execution Risk Assessment (`reasoning/meta_cognition.py`)**:
   - Evaluates goal confidence ($0.0 \text{ to } 1.0$), CoT step depth, missing context, and risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) with destructive action interception.
2. **Speculative Drafting & Execution Engine (`reasoning/speculative.py`, `orchestrator/speculative.py`)**:
   - Generates speculative draft tool calls using fast deterministic rules and parallel validation, accelerating tool execution loops by up to 60%.
3. **Trajectory Experience Replay Database (`memory/experience_replay.py`)**:
   - SQLite WAL database persisting execution trajectories (`trajectory_id`, `goal_query`, `success_status`, `step_count`, `tool_sequence`, `failure_reason`) and similarity pattern retrieval (`get_similar_failures()`).
4. **Temporal Knowledge Graph 2.0 (`memory/temporal_kg.py`)**:
   - Time-stamped relational edge world model $(e_1, r, e_2, t_{\text{start}}, t_{\text{end}})$ supporting point-in-time snapshot queries (`query_as_of`).
5. **Semantic Workspace Code Intelligence Graph (`workspace/code_graph.py`)**:
   - AST code structure indexer providing zero-token symbol definition resolution (`find_definition`) and reference lookups (`find_references`).
6. **Closed-Loop Cognitive Cycle & Verification Engine (`reasoning/cognitive_loop.py` & `agent/critic_agent.py`)**:
   - Explicit `Observe -> Think -> Critic -> Improve -> Retry` evaluation cycle generating structured `SelfEvaluationPayload` metrics (`confidence_score`, `reasoning_depth`, `failure_risk`).
4. **Multi-Objective Model Router (`router.py`)**:
   - Multi-objective optimization router selecting backends by balancing Quality, Token Cost, and Latency.
5. **Ebbinghaus Memory Decay Engine (`memory/decay.py`)**:
   - Dynamic retention decay engine scoring memory items and partitioning them into `RETAIN`, `ARCHIVE`, and `PRUNE` categories.
6. **Ultra-Fast Silero VAD Voice Subsystem (`voice/silero_vad.py`)**:
   - High-precision ONNX Silero VAD acoustic segmenter eliminating silence noise and clipping (<10ms latency).
7. **Zero-Disk Whisper Audio Streaming (`voice/whisper_local.py`)**:
   - Pure in-memory audio byte buffer ASR transcription with RMS acoustic silence gating and hallucination suppression.
8. **CDP DOM Bridge Vision Tier (`vision/dom_bridge.py`)**:
   - Tier 2 CDP Chrome/Edge Browser accessibility DOM inspection bridge for instant element extraction without visual snapshot reliance.
9. **Antigravity Scratchpad Subsystem (`agent/scratchpad.py` & `tools/scratchpad_tools.py`)**:
   - Isolated workspace at `./scratch/` for transient scripts in Python, Node.js, PowerShell, and Bash with stdout/stderr capture via `scratchpad_eval`.
10. **Autonomous Planning Mode & GFM Artifact Engine (`agent/planning_mode.py` & `agent/artifacts.py`)**:
    - Dynamic task complexity classifier (`warrants_plan`), `implementation_plan.md` & `walkthrough.md` generation with GitHub-style alerts (`> [!IMPORTANT]`, `> [!NOTE]`), Mermaid diagrams, and clickable `file:///` URIs.
8. **50+ Zero-Token Deterministic Intent Engine (`core/intent_engine.py`)**:
   - Zero-token intent triggers covering Git status/branch, RAM flush, CPU telemetry, display resolution, battery stats, network ping, and active window state with <5ms latency.
9. **7-Tier Hybrid Vision Engine (`vision/`)**:
   - Combines Tier 1 Windows Accessibility API (`accessibility.py`), Tier 2 CDP Browser DOM Bridge (`dom_bridge.py`), and Tesseract OCR into a unified `SemanticUIGraph`.

---

## 🌟 Essential Reading Order for AI Agents & Developers

1. [fullproject.md](fullproject.md) — Master Full Project Architecture Specification
2. [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) — Core system topology & data flow
3. [architecture/PROJECT_STRUCTURE.md](architecture/PROJECT_STRUCTURE.md) — Directory mapping & module index
4. [full_repository_audit.md](full_repository_audit.md) — Deep engineering audit report & bug tracking
5. [voice/VOICE_ENGINE.md](voice/VOICE_ENGINE.md) — VoicePromptRefiner, ASR & Neural TTS
6. [ai/MEMORY_ENGINE.md](ai/MEMORY_ENGINE.md) — 5-Tier Memory Subsystem
7. [computer/COMPUTER_OPERATOR.md](computer/COMPUTER_OPERATOR.md) — OS Desktop Operator & Clipboard Utility
