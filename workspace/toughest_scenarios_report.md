# ⚡ JARVIS MK37 Toughest Scenarios Test Report

**Date:** 2026-07-25 12:54:55
**Results:** 8/10 Test Cases Passed

| Component | Status | Latency | Scenario Details |
| :--- | :---: | :---: | :--- |
| **1. VOICE (Edge TTS Fallback Mode)** | PASS | `121.06ms` | Successfully initialized fallback TTS engine cleanly |
| **2. CLI (Complex Reasoning Task)** | PASS | `21990.43ms` | Response: '838047729' (Expected to contain: 838047729) |
| **3. BOTH (Voice + CLI Coexistence)** | PASS | `24546.65ms` | CLI and Voice Assistant threads ran concurrently without locks |
| **4. WEB CORE (FastAPI Concurrency)** | FAIL | `4018.21ms` | Local server at http://localhost:8000 is not running. |
| **5. STATUS (Telemetry Reporting)** | FAIL | `4102.14ms` | Error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /api/status (Caused by NewConnectionError("HTTPConnection(host='localhost', port=8000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) |
| **6. DOCTOR (Module Diagnostics)** | PASS | `0.91ms` | Properly caught missing package. Result: (False, 'No module named 'non_existent_module_xyz_123'') |
| **7. SMOKE (Startup Sanity checks)** | PASS | `348.99ms` | All 10/10 non-destructive startup checks passed successfully |
| **8. AUDIO (VAD Energy Corner Cases)** | PASS | `0.08ms` | Processed silence, underflow, and overflow inputs cleanly. Native Active: False |
| **9. LIVE OS (Risk Safety Constraints)** | PASS | `0.01ms` | Constructed LiveOSController with goal: 'delete absolute path files in directory ...' safely. |
| **10. FLOATING (Headless UI Grace)** | PASS | `1238.02ms` | Tkinter UI initialized and closed successfully |