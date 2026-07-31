# ⚡ JARVIS MK37 Toughest Scenarios Test Report

**Date:** 2026-07-31 10:40:45
**Results:** 6/10 Test Cases Passed

| Component | Status | Latency | Scenario Details |
| :--- | :---: | :---: | :--- |
| **1. VOICE (Edge TTS Fallback Mode)** | PASS | `215.99ms` | Successfully initialized fallback TTS engine cleanly |
| **2. CLI (Complex Reasoning Task)** | PASS | `25211.03ms` | Response: '838047729' (Expected to contain: 838047729) |
| **3. BOTH (Voice + CLI Coexistence)** | PASS | `22461.25ms` | CLI and Voice Assistant threads ran concurrently without locks |
| **4. WEB CORE (FastAPI Concurrency)** | FAIL | `4025.92ms` | Local server at http://localhost:8000 is not running. |
| **5. STATUS (Telemetry Reporting)** | FAIL | `4075.76ms` | Error: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /api/status (Caused by NewConnectionError("HTTPConnection(host='localhost', port=8000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) |
| **6. DOCTOR (Module Diagnostics)** | PASS | `0.93ms` | Properly caught missing package. Result: (False, 'No module named 'non_existent_module_xyz_123'') |
| **7. SMOKE (Startup Sanity checks)** | FAIL | `242.50ms` | Error:  |
| **8. AUDIO (VAD Energy Corner Cases)** | PASS | `0.06ms` | Processed silence, underflow, and overflow inputs cleanly. Native Active: False |
| **9. LIVE OS (Risk Safety Constraints)** | FAIL | `0.23ms` | Error:  |
| **10. FLOATING (Headless UI Grace)** | PASS | `801.10ms` | Tkinter UI initialized and closed successfully |