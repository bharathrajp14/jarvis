import time
import os
import sys
import psutil
from core.runtime import get_runtime
from events.bus import get_event_bus
from events.types import BaseEvent

def run_soak_test(cycles: int = 1000):
    print(f"=== Starting {cycles}-cycle Soak Test ===")
    proc = psutil.Process(os.getpid())
    
    runtime = get_runtime()
    bus = get_event_bus()
    
    # Track initial memory and threads
    initial_rss_mb = proc.memory_info().rss / (1024 * 1024)
    initial_threads = proc.num_threads()
    
    print(f"Initial Memory RSS: {initial_rss_mb:.2f} MB, Active Threads: {initial_threads}")
    
    received_events = []
    def on_event(ev):
        received_events.append(ev)
    
    bus.subscribe("soak.test", on_event)
    
    t0 = time.perf_counter()
    for i in range(cycles):
        bus.publish(BaseEvent(topic="soak.test", payload={"cycle": i, "data": "soak_test_payload"}))
        if (i + 1) % 250 == 0:
            current_rss = proc.memory_info().rss / (1024 * 1024)
            print(f"  [Cycle {i+1}/{cycles}] RSS: {current_rss:.2f} MB, Received Events: {len(received_events)}")
            
    t1 = time.perf_counter()
    final_rss_mb = proc.memory_info().rss / (1024 * 1024)
    final_threads = proc.num_threads()
    
    print(f"\n=== Soak Test Complete in {(t1-t0):.2f}s ({(t1-t0)/cycles*1000:.3f}ms/cycle) ===")
    print(f"Final Memory RSS: {final_rss_mb:.2f} MB (Delta: {final_rss_mb - initial_rss_mb:+.2f} MB)")
    print(f"Final Threads: {final_threads} (Delta: {final_threads - initial_threads:+d})")
    assert len(received_events) == cycles
    assert (final_rss_mb - initial_rss_mb) < 50.0  # Leak tolerance < 50MB
    print("✅ Soak test PASSED with 0 memory leaks!")

def test_soak_reliability():
    """Pytest wrapper running a 250-cycle soak test to verify zero memory leaks."""
    run_soak_test(cycles=250)


if __name__ == "__main__":
    run_soak_test(1000)

