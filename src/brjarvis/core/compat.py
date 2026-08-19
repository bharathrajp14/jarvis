# core/compat.py
"""
Backward-compatible shim layer for JARVIS MK37.

Re-exports any renamed or moved symbols so existing skills/,
agents/, and markdown configuration files continue working
even after internal refactors.

Usage:
    from core.compat import *
"""

from __future__ import annotations

# ── Re-export core orchestration symbols ──────────────────────────────────
try:
    from brjarvis.orchestrator.core import JarvisOrchestrator
except ImportError:
    try:
        from orchestrator import JarvisOrchestrator
    except ImportError:
        JarvisOrchestrator = None  # type: ignore[assignment,misc]

try:
    from brjarvis.router.core import ROUTING_RULES, AgentProfile, AgentRouter
except ImportError:
    try:
        from router import ROUTING_RULES, AgentProfile, AgentRouter
    except ImportError:
        AgentRouter = None  # type: ignore[assignment,misc]
        AgentProfile = None  # type: ignore[assignment,misc]
        ROUTING_RULES = {}

# ── Re-export memory symbols ─────────────────────────────────────────────
try:
    from brjarvis.memory.working import WorkingMemory
except ImportError:
    try:
        from memory.working import WorkingMemory
    except ImportError:
        WorkingMemory = None  # type: ignore[assignment,misc]

try:
    from brjarvis.memory.persistent_store import (
        MemoryEntry,
        delete_memory,
        load_entries,
        load_index,
        save_memory,
        search_memory,
    )
except ImportError:
    try:
        from memory.persistent_store import (
            MemoryEntry,
            delete_memory,
            load_entries,
            load_index,
            save_memory,
            search_memory,
        )
    except ImportError:
        MemoryEntry = None  # type: ignore[assignment,misc]
        save_memory = None  # type: ignore[assignment]
        delete_memory = None  # type: ignore[assignment]
        load_entries = None  # type: ignore[assignment]
        load_index = None  # type: ignore[assignment]
        search_memory = None  # type: ignore[assignment]

try:
    from brjarvis.memory.vector_store import VectorMemory
except ImportError:
    try:
        from memory.vector_store import VectorMemory
    except ImportError:
        VectorMemory = None  # type: ignore[assignment,misc]

try:
    from brjarvis.memory.consolidator import consolidate_session
except ImportError:
    try:
        from memory.consolidator import consolidate_session
    except ImportError:
        consolidate_session = None  # type: ignore[assignment]

try:
    from brjarvis.memory.memory_context import find_relevant_memories, get_memory_context
except ImportError:
    try:
        from memory.memory_context import find_relevant_memories, get_memory_context
    except ImportError:
        get_memory_context = None  # type: ignore[assignment]
        find_relevant_memories = None  # type: ignore[assignment]

# ── Re-export tool symbols ───────────────────────────────────────────────
try:
    from brjarvis.tools.registry import (
        TOOL_SCHEMAS,
        execute_tool,
        get_tool_prompt_block,
        parse_tool_call,
    )
except ImportError:
    try:
        from tools.registry import (
            TOOL_SCHEMAS,
            execute_tool,
            get_tool_prompt_block,
            parse_tool_call,
        )
    except ImportError:
        TOOL_SCHEMAS = []
        get_tool_prompt_block = None  # type: ignore[assignment]
        parse_tool_call = None  # type: ignore[assignment]
        execute_tool = None  # type: ignore[assignment]

try:
    from brjarvis.tools.sandbox import CodeSandbox
except ImportError:
    try:
        from tools.sandbox import CodeSandbox
    except ImportError:
        CodeSandbox = None  # type: ignore[assignment,misc]

try:
    from brjarvis.tools.files import FileManager
except ImportError:
    try:
        from tools.files import FileManager
    except ImportError:
        FileManager = None  # type: ignore[assignment,misc]

# ── Re-export skills symbols ─────────────────────────────────────────────
try:
    from brjarvis.skills.loader import SkillDef, find_skill, load_skills, substitute_arguments
except ImportError:
    try:
        from skills.loader import SkillDef, find_skill, load_skills, substitute_arguments
    except ImportError:
        SkillDef = None  # type: ignore[assignment,misc]
        load_skills = None  # type: ignore[assignment]
        find_skill = None  # type: ignore[assignment]
        substitute_arguments = None  # type: ignore[assignment]

try:
    from brjarvis.skills.executor import execute_skill
except ImportError:
    try:
        from skills.executor import execute_skill
    except ImportError:
        execute_skill = None  # type: ignore[assignment]

# ── Re-export multi-agent symbols ────────────────────────────────────────
try:
    from brjarvis.multi_agent.subagent import (
        AgentDefinition,
        SubAgentManager,
        SubAgentTask,
        get_agent_definition,
        load_agent_definitions,
    )
except ImportError:
    try:
        from multi_agent.subagent import (
            AgentDefinition,
            SubAgentManager,
            SubAgentTask,
            get_agent_definition,
            load_agent_definitions,
        )
    except ImportError:
        AgentDefinition = None  # type: ignore[assignment,misc]
        SubAgentTask = None  # type: ignore[assignment,misc]
        SubAgentManager = None  # type: ignore[assignment,misc]
        load_agent_definitions = None  # type: ignore[assignment]
        get_agent_definition = None  # type: ignore[assignment]

# ── Re-export permissions ────────────────────────────────────────────────
try:
    from brjarvis.security.permissions import PERMISSIONS, PermissionMode, PermissionPolicy
except ImportError:
    try:
        from permissions import PERMISSIONS, PermissionMode, PermissionPolicy
    except ImportError:
        PERMISSIONS = None  # type: ignore[assignment]
        PermissionPolicy = None  # type: ignore[assignment,misc]
        PermissionMode = None  # type: ignore[assignment,misc]

# ── Re-export history ────────────────────────────────────────────────────
try:
    from brjarvis.history.session_store import SessionStore
except ImportError:
    try:
        from history.session_store import SessionStore
    except ImportError:
        SessionStore = None  # type: ignore[assignment,misc]

try:
    from brjarvis.history.audit_writer import write_audit
except ImportError:
    try:
        from history.audit_writer import write_audit
    except ImportError:
        write_audit = None  # type: ignore[assignment]

# ── Re-export backends ───────────────────────────────────────────────────
try:
    from brjarvis.integrations.backends.gemini import GeminiBackend
except Exception:
    GeminiBackend = None  # type: ignore[assignment,misc]

try:
    from brjarvis.integrations.backends.anthropic import ClaudeBackend
except Exception:
    ClaudeBackend = None  # type: ignore[assignment,misc]

try:
    from brjarvis.integrations.backends.openai_compat import OpenAIBackend
except Exception:
    OpenAIBackend = None  # type: ignore[assignment,misc]

try:
    from brjarvis.integrations.backends.ollama import OllamaBackend
except Exception:
    OllamaBackend = None  # type: ignore[assignment,misc]

try:
    from brjarvis.integrations.backends.nvidia import NvidiaBackend
except Exception:
    NvidiaBackend = None  # type: ignore[assignment,misc]

try:
    from brjarvis.integrations.backends.mistral import MistralBackend
except Exception:
    MistralBackend = None  # type: ignore[assignment,misc]

# ── Re-export config ─────────────────────────────────────────────────────
try:
    from brjarvis.config.models import get_model, get_model_config
except ImportError:
    try:
        from config.models import get_model, get_model_config
    except ImportError:
        get_model = None  # type: ignore[assignment]
        get_model_config = None  # type: ignore[assignment]


__all__ = [
    # Core
    "JarvisOrchestrator",
    "AgentRouter",
    "AgentProfile",
    "ROUTING_RULES",
    # Memory
    "WorkingMemory",
    "VectorMemory",
    "MemoryEntry",
    "save_memory",
    "delete_memory",
    "load_entries",
    "load_index",
    "search_memory",
    "consolidate_session",
    "get_memory_context",
    "find_relevant_memories",
    # Tools
    "TOOL_SCHEMAS",
    "get_tool_prompt_block",
    "parse_tool_call",
    "execute_tool",
    "CodeSandbox",
    "FileManager",
    # Skills
    "SkillDef",
    "load_skills",
    "find_skill",
    "substitute_arguments",
    "execute_skill",
    # Agents
    "AgentDefinition",
    "SubAgentTask",
    "SubAgentManager",
    "load_agent_definitions",
    "get_agent_definition",
    # Permissions
    "PERMISSIONS",
    "PermissionPolicy",
    "PermissionMode",
    # History
    "SessionStore",
    "write_audit",
    # Backends
    "GeminiBackend",
    "ClaudeBackend",
    "OpenAIBackend",
    "OllamaBackend",
    "NvidiaBackend",
    "MistralBackend",
    # Config
    "get_model",
    "get_model_config",
]
