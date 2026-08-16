# BR JARVIS Android Companion App Architecture (`mobile/android/`)

## Overview

The **BR JARVIS Android Companion** transforms an authorized Android phone into a secure, controlled node within the JARVIS multi-device operating system.

---

## 1. Core Android Subsystems

```text
                  JARVIS Desktop Core (server.py / gateway.py)
                                  │
                       TLS / WebSocket (WSS)
                                  │
                      Android Companion Client
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          JarvisAccessibilityService   JarvisMediaProjectionService
                    │                           │
          Semantic UI Tree + Actions     Screen Frame Stream
```

### 1. `JarvisAccessibilityService`
- Listens for window and accessibility events (`AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED`, `TYPE_VIEW_CLICKED`).
- Traverses `AccessibilityNodeInfo` hierarchy and packages nodes into JSON-RPC messages (`node_id`, `class_name`, `text`, `bounds`, `clickable`, `editable`).
- Performs semantic actions: `performAction(AccessibilityNodeInfo.ACTION_CLICK)`, `ACTION_SET_TEXT`, `ACTION_SCROLL_FORWARD`.
- Handles global navigation: `performGlobalAction(GLOBAL_ACTION_HOME)`, `GLOBAL_ACTION_BACK`, `GLOBAL_ACTION_RECENTS`.

### 2. `JarvisMediaProjectionService`
- Captures screen frames when explicit user projection permission is granted (`MediaProjectionManager.createScreenCaptureIntent()`).
- Encodes frames into WebP / JPEG chunks and streams over the secure WebSocket channel.

### 3. `DeviceStateService`
- BroadcastReceiver for `ACTION_BATTERY_CHANGED`, `CONNECTIVITY_ACTION`, and `KeyguardManager.isDeviceLocked()`.
- Sends real-time device telemetry and lock events to JARVIS.

---

## 2. Secure Pairing Protocol

1. User clicks **"Pair New Mobile Device"** in JARVIS Control Center.
2. JARVIS generates a temporary 6-digit PIN and SHA256 auth token.
3. User opens JARVIS Android App and scans QR code or enters the PIN.
4. Android Companion establishes mutual TLS connection and exchanges public keys.
5. JARVIS saves device identity in `workspace/devices/devices.db` with state `TRUSTED`.

---

## 3. Strict Security & Lock State Invariants

- **Zero Bypass**: The app NEVER attempts to defeat PIN, pattern, password, or biometric locks.
- **Lock Reporting**: When `KeyguardManager.isDeviceLocked()` returns `true`, JARVIS halts automation and enters `WAITING_FOR_USER_AUTHENTICATION`.
- **Approval Gates**: Sensitive actions (sending messages, deleting files, purchasing) require explicit confirmation before execution.
