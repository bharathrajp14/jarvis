# 🧠 Memory Engine Architectural Specification

> **Module**: `memory/`  
> **Version**: MK37.31.0  
> **Primary Purpose**: Multi-tier memory retention, Knowledge Graph world model, Ebbinghaus memory decay, ChromaDB vector RAG, and instant FNV-1a response caching.

---

## 1. 6-Tier Memory Architecture

BR JARVIS employs a 6-tier memory subsystem managed by `UnifiedMemoryManager` (`memory/manager.py`).

```
                    ┌─────────────────────────┐
                    │      User Prompt        │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
┌──────────────────┐                           ┌──────────────────┐
│  Tier 1: Working │                           │  Tier 5: FNV-1a  │
│  Memory (RAM)    │                           │  Response Cache  │
└────────┬─────────┘                           └────────┬─────────┘
         │                                              │
         ▼                                              ▼
┌──────────────────┐                           ┌──────────────────┐
│  Tier 2: SQLite  │                           │  Tier 4: Lesson  │
│  Session DB      │                           │  Store (Markdown)│
└────────┬─────────┘                           └────────┬─────────┘
         │                                              │
         ├───────────────────────┬──────────────────────┘
         ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│  Tier 3: ChromaDB│   │ Tier 6: NetworkX │
│  Vector RAG      │   │ Knowledge Graph  │
└──────────────────┘   └──────────────────┘
```

---

## 2. Subsystem Tier Breakdown

### Tier 1: Short-Term Working Memory (`memory/working.py`)
- Maintains in-memory session turn state (`turn_history`) during an active goal execution.
- Features turn recording helpers: `add_user_message()`, `add_assistant_message()`, `_record_turn()`.
- Thread-safe access protected by re-entrant locks (`RLock`).

### Tier 2: Persistent Conversation Store (`memory/persistent_store.py` & `memory/conversation_store.py`)
- SQLite WAL-backed store persisting user interactions, execution logs, and turn histories across restarts (`memory_db/`).
- Enforces `PRAGMA journal_mode=WAL;` and `timeout=20.0` for multi-threaded lock protection.

### Tier 3: Semantic Vector RAG (`memory/vector_store.py` & `memory/rag.py`)
- Embedded ChromaDB vector database generating semantic embeddings for file contents, previous solutions, and web research notes.

### Tier 4: Architectural Lessons Store (`memory/lessons.py`)
- Persistent Markdown store (`memory/lessons/`) containing self-correction rules, error recovery lessons, and user feedback preferences.

### Tier 5: Fast Hashing Response Cache (`memory/cache.py`)
- Fast FNV-1a hash caching for read-only tool responses and vision screenshot frames.

### Tier 6: Relational Knowledge Graph World Model (`memory/knowledge_graph.py`)
- NetworkX relational entity graph connecting `Workspace`, `Projects`, `Files`, `Apps`, `Windows`, `Goals`, `Repositories`, and `APIs`.

### Memory Decay & Forgetting Engine (`memory/decay.py`)
- Implements Ebbinghaus memory decay:
  $$\text{RetentionScore} = \text{Importance} \times e^{-\text{decay\_rate} \times \text{elapsed\_time}} \times (1 + \log(\text{access\_count}))$$
- Classifies memories into `RETAIN`, `ARCHIVE`, and `PRUNE` categories to prevent memory bloat.
- In-memory & disk-backed cache keying tool outputs and deterministic queries by FNV-1a frame/query hashes for instant hit resolution (<1ms).
