"""Bootstrap test script — validates the full startup chain."""
import sys
import os
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("=== BR JARVIS Bootstrap Validation ===")
print()

# 1. Config
try:
    from core.config import get_config
    cfg = get_config()
    print("[OK] core.config: default_backend=%s, gemini=%s" % (cfg.models.default_backend, cfg.models.gemini))
except Exception as e:
    print("[FAIL] core.config: %s" % e)

# 2. Permissions
try:
    import permissions
    print("[OK] permissions: mode=%s" % permissions.PERMISSIONS.mode.value)
except Exception as e:
    print("[FAIL] permissions: %s" % e)

# 3. Events
try:
    from events.bus import get_event_bus
    bus = get_event_bus()
    print("[OK] events.bus: EventBus ready")
except Exception as e:
    print("[FAIL] events.bus: %s" % e)

# 4. Gemini Backend
try:
    from backends.gemini import GeminiBackend
    g = GeminiBackend()
    proxy = g._use_openai_client
    print("[OK] backends.gemini: model=%s, proxy=%s, available=%s" % (g.model, proxy, g.available))
except Exception as e:
    print("[FAIL] backends.gemini: %s" % e)

# 5. Router
try:
    from router import load_available_backends, AgentRouter
    backends = load_available_backends()
    names = [b.value for b in backends.keys()]
    router = AgentRouter(backends)
    print("[OK] router: backends=%s, default=%s" % (names, router.default.value))
except Exception as e:
    print("[FAIL] router: %s" % e)

# 6. Tools registry
try:
    from tools.registry import TOOL_SCHEMAS, _import_plugins
    _import_plugins()
    print("[OK] tools.registry: %d tools registered" % len(TOOL_SCHEMAS))
except Exception as e:
    print("[FAIL] tools.registry: %s" % e)

# 7. Full bootstrap
try:
    from core.bootstrap import build_assistant_runtime
    runtime = build_assistant_runtime()
    print("[OK] core.bootstrap: AssistantRuntime built")
    print("     orchestrator: %s" % type(runtime.orchestrator).__name__)
    print("     router default: %s" % runtime.router.default.value)
except Exception as e:
    print("[FAIL] core.bootstrap: %s" % e)

print()
print("=== Validation Complete ===")
