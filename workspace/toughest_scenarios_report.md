# ⚡ JARVIS MK37 Toughest Scenarios Test Report

**Date:** 2026-07-31 10:52:25
**Results:** 6/10 Test Cases Passed

| Component | Status | Latency | Scenario Details |
| :--- | :---: | :---: | :--- |
| **1. VOICE (Edge TTS Fallback Mode)** | PASS | `42.70ms` | Successfully initialized fallback TTS engine cleanly |
| **2. CLI (Complex Reasoning Task)** | PASS | `24028.18ms` | Response: '838047729' (Expected to contain: 838047729) |
| **3. BOTH (Voice + CLI Coexistence)** | PASS | `19992.58ms` | CLI and Voice Assistant threads ran concurrently without locks |
| **4. WEB CORE (FastAPI Concurrency)** | FAIL | `4019.81ms` | Local server at http://localhost:8000 is not running. |
| **5. STATUS (Telemetry Reporting)** | FAIL | `4094.22ms` | Error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /api/status (Caused by NewConnectionError("HTTPConnection(host='localhost', port=8000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) |
| **6. DOCTOR (Module Diagnostics)** | PASS | `0.67ms` | Properly caught missing package. Result: (False, 'No module named 'non_existent_module_xyz_123'') |
| **7. SMOKE (Startup Sanity checks)** | PASS | `246.06ms` | All 10/10 non-destructive startup checks passed successfully |
| **8. AUDIO (VAD Energy Corner Cases)** | PASS | `0.07ms` | Processed silence, underflow, and overflow inputs cleanly. Native Active: False |
| **9. LIVE OS (Risk Safety Constraints)** | FAIL | `0.18ms` | Error:  |
| **10. FLOATING (Headless UI Grace)** | FAIL | `0.54ms` | Error: No module named 'floating_voice_ui' |