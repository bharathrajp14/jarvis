# gateway/probe.py — Live Diagnostic Probe for Proxy Brain Models
"""
Command-line probe utility testing the local Proxy Brain gateway.
Discovers models, performs concurrent ping probes, categorizes capabilities,
and outputs recommended defaults without exposing credentials.

Usage:
  python -m gateway.probe
"""
from __future__ import annotations

import concurrent.futures
import logging
import sys
import time

# Ensure UTF-8 output on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .client import get_proxy_brain_client
from .discovery import get_discovery_service
from .health import HealthState, get_health_service
from brjarvis.router.smart_router import get_smart_router
from brjarvis.router.task_profile import TaskComplexity, TaskProfile

# Configure minimal console logging for clean probe output
logging.basicConfig(level=logging.WARNING, format="%(message)s")


def run_probe():
    client = get_proxy_brain_client()
    discovery = get_discovery_service()
    health = get_health_service()
    router = get_smart_router()

    print("Proxy Brain Gateway Probe")
    print("=" * 65)
    print(f"Base URL:           {client.base_url}")
    print(f"Preferred Provider: Gemini (Primary Policy)")
    print("-" * 65)

    # 1. Discover Models
    t0 = time.monotonic()
    models = discovery.discover_models(force_refresh=True)
    discovery_dt = int((time.monotonic() - t0) * 1000)

    if not models:
        print("Status: [OFFLINE / UNREACHABLE]")
        print("Could not retrieve models from Proxy Brain gateway.")
        return

    print(f"Status:             [ONLINE] ({discovery_dt} ms)")
    print(f"Models Discovered:  {len(models)}")
    print("-" * 65)
    print("Executing quick concurrent health verification...")

    def ping_model(m_id: str):
        t_start = time.monotonic()
        try:
            resp = client.complete(
                model=m_id,
                messages=[{"role": "user", "content": "respond with exactly: pong"}],
                max_tokens=10,
                temperature=0.1
            )
            lat = int((time.monotonic() - t_start) * 1000)
            health.record_success(m_id, lat)
            return {"model": m_id, "status": "ONLINE", "latency": lat, "reply": resp.text.strip().replace("\n", " ")[:30]}
        except Exception as exc:
            lat = int((time.monotonic() - t_start) * 1000)
            is_quota = "quota" in str(exc).lower() or "503" in str(exc)
            health.record_failure(m_id, str(exc), is_quota=is_quota)
            return {"model": m_id, "status": "OFFLINE", "latency": lat, "error": str(exc)[:40]}

    # Test discovered models concurrently
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(ping_model, m.id): m.id for m in models}
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    healthy = [r for r in results if r["status"] == "ONLINE"]
    unavailable = [r for r in results if r["status"] == "OFFLINE"]

    print(f"Healthy / Active:   {len(healthy)}")
    print(f"Unavailable:        {len(unavailable)}")
    print("=" * 65)

    # 2. Dynamic Task Profile Routing Recommendations
    print("\nDynamic Recommended Defaults (Derived from Live Gateway State):")
    print("-" * 65)

    categories = [
        ("FAST (Low Latency)", TaskProfile(task_type="fast_chat", complexity=TaskComplexity.LOW, latency_sensitive=True)),
        ("GENERAL (Assistant)", TaskProfile(task_type="chat", complexity=TaskComplexity.MEDIUM)),
        ("REASONING (Deep)", TaskProfile(task_type="reasoning", complexity=TaskComplexity.HIGH, requires_reasoning=True)),
        ("CODE (Engineering)", TaskProfile(task_type="code", complexity=TaskComplexity.HIGH, requires_code=True)),
        ("AGENT (Multi-Step)", TaskProfile(task_type="agent", complexity=TaskComplexity.HIGH, requires_tools=True, requires_agent=True)),
        ("VISION (Screen/Image)", TaskProfile(task_type="vision", complexity=TaskComplexity.MEDIUM, requires_vision=True)),
    ]

    for title, profile in categories:
        selection = router.route(profile)
        rec = health.get_health(selection.model_id)
        lat_str = f"{int(rec.latency_ms)} ms" if rec.latency_ms > 0 else "unmeasured"
        print(f"  • {title:<24} -> {selection.model_id:<28} | Score: {selection.score} | Latency: {lat_str}")

    print("-" * 65)
    print("Fallback Diversity Candidates:")
    claude_models = [m.id for m in models if "claude" in m.id.lower() and health.is_available(m.id)]
    gpt_models = [m.id for m in models if "gpt" in m.id.lower() and health.is_available(m.id)]
    print(f"  • Claude: {', '.join(claude_models[:4]) if claude_models else 'None active'}")
    print(f"  • GPT:    {', '.join(gpt_models[:4]) if gpt_models else 'None active'}")
    print("=" * 65)


if __name__ == "__main__":
    run_probe()
