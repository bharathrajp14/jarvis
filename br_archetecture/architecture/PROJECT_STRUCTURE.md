# 📂 Codebase Directory Mapping & Module Responsibilities

> **System**: BR JARVIS (MK37.30.0)  
> **Scale**: ~180 Python files across 30 top-level packages.

---

## 1. Directory Tree & Module Mapping

```
Br-Jarvis/
├── actions/                   # OS automation (browser, desktop, apps, games, file ops)
│   ├── clipboard_utils.py     # 5-tier prioritized clipboard fallback engine
│   ├── live_os_control.py     # LLM screenshot action execution & visual trace overlays
│   └── ...                    # 34 action modules
├── agent/                     # Autonomous planning & execution pipeline
│   ├── artifacts.py           # GFM Artifact Engine (implementation_plan.md, walkthrough.md)
│   ├── executor.py            # GoalGraph worker execution pool
│   ├── planner.py             # Plan DAG generator & complexity evaluation
│   ├── planning_mode.py       # Autonomous Planning Mode logic (`warrants_plan`)
│   ├── scratchpad.py          # Antigravity Scratchpad workspace evaluator (`./scratch/`)
│   ├── step_planner.py        # Conscious Step Planner & AdaptiveStepBudget controller
│   └── transcript_logger.py   # Trajectory JSON Lines transcript logger (`transcript.jsonl`)
├── backends/                  # AI Provider Adapters (Gemini, Claude, GPT, Ollama, DeepSeek, NVIDIA, Mistral)
├── br_archetecture/           # Persistent Engineering Knowledge Base index & specifications
├── computer/                  # Desktop operator & OS window management
│   ├── operator.py            # PyAutoGUI desktop operator & win32 handle manager
│   ├── recovery.py            # Self-healing popup recovery engine
│   ├── semantic_operator.py   # UI node dynamic finder
│   └── types.py               # Action, coordinate, and target models
├── config/                    # Configuration settings, key maps, vocabulary.json
├── context/                   # Context assembly, sliding windows, reference resolution
├── core/                      # Core runtime, DI container, retry, intent engine, error middleware
│   └── intent_engine.py       # 50+ zero-token instant deterministic intent matchers
├── events/                    # Asynchronous Pub/Sub EventBus & event models
├── evolution/                 # Self-upgrade sandbox, classifier, proposer, deployer
├── guardian/                  # PathPolicy bounds check, kill-switch, snapshot, rollback
├── history/                   # Session store, replay engine, transcript writer
├── memory/                    # 5-tier memory subsystem (Working, SQLite, Vector RAG, Lessons, Cache)
├── multi_agent/               # Sub-agent spawning framework (12 subagent definitions)
├── native/                    # Win32 C native bridge (`jarvis_native.c`)
├── plugins/                   # Plugin platform & isolation manager
├── reasoning/                 # Chain-of-Thought engine, plan graph DAG
├── redteam/                   # Recon scanner, security auditor, scope manager
├── screen_server/             # Real-time WebSocket screen share server
├── skills/                    # Skill loader & builtins (RAG, Auditor, Writer, Excel)
├── tools/                     # Tool registry & 34 tool modules (scratchpad_tools, browser_tools, etc.)
├── vision/                    # 7-tier hybrid vision engine (Accessibility API, CDP DOM bridge, OCR)
├── voice/                     # Voice system (Whisper ASR, Neural TTS, prompt refiner, wake word)
│   └── prompt_refiner.py      # VoicePromptRefiner vocal filler cleaner & vocabulary mapper
├── web/                       # Glassmorphic PWA Web UI dashboard (HTML/CSS/JS)
├── workflow/                  # Durable workflow DAG engine & SQLite state store
├── floating_voice_ui.py       # Gemini Live floating overlay UI
├── main_mk37.py               # Rich TUI CLI launcher
├── orchestrator.py            # Core ReAct reasoning & execution loop
├── permissions.py             # Security policy & permission matrix
├── router.py                  # Dynamic multi-backend AI model router
├── server.py                  # FastAPI REST & WebSocket server
├── start.py                   # System entry point launcher
└── ui.py                      # Tkinter Maximum Control Center HUD (72KB monolith)
```
