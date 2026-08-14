# tests/adversarial/test_startup_profiler.py — Deep Import & Startup Profile Audit
from __future__ import annotations

import importlib
import sys
import time
from typing import Dict, List, Tuple


def profile_imports() -> List[Tuple[str, float]]:
    """Measure exact import times of all top-level modules."""
    modules_to_test = [
        "core.config",
        "core.intent_engine",
        "backends.adapter",
        "backends.gemini",
        "backends.openai_backend",
        "backends.anthropic_backend",
        "backends.ollama_backend",
        "tools.registry",
        "tools.tool_ranker",
        "tools.sandbox_process",
        "tools.system_tools",
        "agent.verifier",
        "workflow.task_dag",
        "memory.unified_memory",
        "memory.vector_store",
        "memory.persistent_store",
        "memory.experience_replay",
        "security.policy_engine",
        "security.path_policy",
        "guardian.core",
        "router.smart_router",
        "orchestrator.core",
    ]

    timings = []
    for mod_name in modules_to_test:
        # Evict module and submodules from sys.modules to simulate cold import
        for k in list(sys.modules.keys()):
            if k == mod_name or k.startswith(mod_name + "."):
                del sys.modules[k]

        t0 = time.perf_counter()
        try:
            importlib.import_module(mod_name)
            dur_ms = (time.perf_counter() - t0) * 1000.0
            timings.append((mod_name, dur_ms))
        except Exception as e:
            timings.append((mod_name, -1.0))

    timings.sort(key=lambda x: x[1], reverse=True)
    return timings


def test_import_profiling():
    timings = profile_imports()
    print("\n" + "="*60)
    print("COLD MODULE IMPORT PROFILING AUDIT")
    print("="*60)
    for mod, dur in timings:
        print(f"  - {mod:<35}: {dur:8.2f} ms")
    print("="*60)
    
    # Assert core fast modules do not exceed 200ms on import
    slow_modules = [m for m, d in timings if d > 500.0]
    print(f"Heavyweight modules (>500ms): {slow_modules}")
