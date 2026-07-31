# ⚡ JARVIS MK37 Toughest Scenarios Test Report

**Date:** 2026-07-31 10:30:54
**Results:** 4/10 Test Cases Passed

| Component | Status | Latency | Scenario Details |
| :--- | :---: | :---: | :--- |
| **1. VOICE (Edge TTS Fallback Mode)** | FAIL | `70.96ms` | Error: 'NeuralTTS' object has no attribute 'is_speaking' |
| **2. CLI (Complex Reasoning Task)** | PASS | `23204.08ms` | Response: '838047729' (Expected to contain: 838047729) |
| **3. BOTH (Voice + CLI Coexistence)** | FAIL | `34572276.92ms` | Error: 'NeuralTTS' object has no attribute 'is_speaking' |
| **4. WEB CORE (FastAPI Concurrency)** | FAIL | `5065.03ms` | Local server at http://localhost:8000 is not running. |
| **5. STATUS (Telemetry Reporting)** | FAIL | `4084.93ms` | Error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /api/status (Caused by NewConnectionError("HTTPConnection(host='localhost', port=8000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) |
| **6. DOCTOR (Module Diagnostics)** | PASS | `1.74ms` | Properly caught missing package. Result: (False, 'No module named 'non_existent_module_xyz_123'') |
| **7. SMOKE (Startup Sanity checks)** | FAIL | `819.80ms` | Error:  |
| **8. AUDIO (VAD Energy Corner Cases)** | PASS | `0.26ms` | Processed silence, underflow, and overflow inputs cleanly. Native Active: False |
| **9. LIVE OS (Risk Safety Constraints)** | FAIL | `0.50ms` | Error:  |
| **10. FLOATING (Headless UI Grace)** | PASS | `2691.80ms` | Tkinter UI initialized and closed successfully |