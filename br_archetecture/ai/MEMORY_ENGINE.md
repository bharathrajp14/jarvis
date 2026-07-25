# 🧠 Memory Engine Architectural Specification

> **Module**: `memory/`  
> **Version**: MK37.31.0  
> **Primary Purpose**: Multi-tier memory retention, conversation session history, ChromaDB vector RAG retrieval, and instant FNV-1a response caching.

---

## 1. 5-Tier Memory Architecture

BR JARVIS employs a 5-tier memory subsystem managed by `UnifiedMemoryManager` (`memory/manager.py`).

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
         └───────────────────────┬──────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Tier 3: ChromaDB Vector│
                    │  RAG Store              │
                    └─────────────────────────┘
```

---

## 2. Subsystem Tier Breakdown

### Tier 1: Short-Term Working Memory (`memory/working.py`)
- Maintains in-memory session turn state (`turn_history`) during an active goal execution.
- Features turn recording helpers: `add_user_message()`, `add_assistant_message()`, `_record_turn()`.
- Thread-safe access protected by re-entrant locks (`RLock`).

### Tier 2: Persistent Conversation Store (`memory/persistent_store.py` & `memory/conversation_store.py`)
- SQLite-backed store persisting user interactions, execution logs, and turn histories across restarts (`memory_db/`).
- Includes automatic migration schema and thread-safe statement execution.

### Tier 3: Semantic Vector RAG (`memory/vector_store.py` & `memory/rag.py`)
- Embedded ChromaDB vector database generating semantic embeddings for file contents, previous solutions, and web research notes.
- Provides similarity search (`search_similar()`) with distance threshold filtering.

### Tier 4: Architectural Lessons Store (`memory/lessons.py`)
- Persistent Markdown store (`memory/lessons/`) containing self-correction rules, error recovery lessons, and user feedback preferences.

### Tier 5: Fast Hashing Response Cache (`memory/cache.py`)
- In-memory & disk-backed cache keying tool outputs and deterministic queries by FNV-1a frame/query hashes for instant hit resolution (<1ms).
