# 🤖 BR JARVIS — Your Autonomous Local AI Assistant

[![CI](https://github.com/bharthraj1412/BrJarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/bharthraj1412/BrJarvis/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-136%2F136%20passing-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

> **BR JARVIS** is your personal, voice-controlled AI assistant that lives directly on your computer. Unlike basic chatbots, JARVIS can actually **see your screen**, **listen to your voice**, **control your apps**, **search your files**, and **do real work on your computer automatically**.

---

## ⚔️ How BR JARVIS Compares to Other Assistants

| Feature | ChatGPT Desktop | Claude Desktop | Cursor / Windsurf | Siri / Windows Copilot | **BR JARVIS** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **🎙️ Voice Command Perception** | ✅ | ❌ | ❌ | ✅ | **✅ (Advanced Noise Gate + Pre-Roll)** |
| **👁️ Reads & Sees Your Screen** | ❌ | ❌ | ❌ | ❌ | **✅ (Real-Time Vision & OCR)** |
| **🖱️ Controls Apps & Desktop** | ❌ | ❌ | ❌ | ⚠️ Limited | **✅ (Full Keyboard, Mouse, & Window Control)** |
| **📂 Searches Your Local Files** | ❌ | ❌ | ✅ Code Only | ⚠️ Basic | **✅ (Natural Language File Finder)** |
| **🩺 Self-Healing Code Doctor** | ❌ | ❌ | ⚠️ Basic | ❌ | **✅ (Auto-Fixes Project Errors)** |
| **💻 Monitors Computer Health** | ❌ | ❌ | ❌ | ❌ | **✅ (Live CPU, RAM, & Battery Telemetry)** |
| **🔒 100% Private & Local** | ❌ Cloud Only | ❌ Cloud Only | ❌ Cloud Only | ❌ Cloud Only | **✅ (Your Data Stays on Your PC)** |

---

## ✨ What Can BR JARVIS Do For You?

| Feature | What JARVIS Does For You |
| :--- | :--- |
| **🎙️ Voice Assistant** | Speak naturally to your computer. JARVIS listens, filters background noise, and speaks back in a clear human voice. |
| **👁️ Sees Your Screen** | Reads text on your screen, spots buttons, and understands what app you have open. |
| **🖱️ Controls Apps & Desktop** | Switches windows, opens apps, clicks buttons, types text, and copies items to your clipboard for you. |
| **📂 Smart File Finder** | Find any document or project by just describing it (e.g. *"Find my voice assistant setup script"*). |
| **🌐 Web Article Reader** | Fetches web pages, strips clutter, and gives you instant key summaries. |
| **💻 System Health Check** | Monitors your computer's CPU speed, RAM memory, storage, and battery level. |
| **🔒 100% Private & Safe** | Your private data stays local on your machine with built-in safety controls. |

---

## 🎯 Example Commands You Can Say To JARVIS

Simply speak or type commands like:

- 🎙️ **"JARVIS, switch to Google Chrome."**
- 📂 **"JARVIS, find my Python configuration file."**
- 💻 **"JARVIS, check my computer's battery and CPU health."**
- 🌐 **"JARVIS, summarize this article for me."**
- 🩺 **"JARVIS, run the code doctor and fix any errors in my project."**
- 🛡️ **"JARVIS, run a security audit on my workspace."**

---

## 💡 How It Works (Simple Overview)

```mermaid
graph LR
    A[🗣️ You Speak or Type] --> B[🧠 JARVIS Understands Your Goal]
    B --> C[⚙️ Picks the Best Tools & Apps]
    C --> D[💻 Executes Work on Your Computer]
    D --> E[🔊 Speaks & Displays Results to You]
```

1. **You Ask**: Speak into your microphone or type a message.
2. **JARVIS Reasons**: Analyzes your request and picks the fastest, safest steps to solve it.
3. **JARVIS Takes Action**: Opens apps, searches files, or writes code safely on your PC.
4. **JARVIS Responds**: Gives you instant spoken and visual updates.

---

## ⚡ Easy 3-Step Setup Guide

You don't need to be an expert programmer to run BR JARVIS! Just follow these 3 steps:

### Step 1: Download & Install
Open your terminal or Command Prompt and run:
```bash
git clone https://github.com/bharthraj1412/BrJarvis.git
cd BrJarvis
pip install -r requirements_mk37.txt
```

### Step 2: Set Your Free Gemini API Key
JARVIS uses Google's Gemini AI engine. Get a free API key from [Google AI Studio](https://ai.google.dev/) and set it:

* **Windows PowerShell**:
  ```powershell
  $env:GEMINI_API_KEY="your-api-key-here"
  ```
* **Linux / Mac**:
  ```bash
  export GEMINI_API_KEY="your-api-key-here"
  ```

### Step 3: Launch JARVIS!
Start your AI assistant:
```bash
python main.py
```

---

## ❓ Frequently Asked Questions (FAQ)

### Is BR JARVIS free to use?
Yes! BR JARVIS is 100% open-source software under the MIT License.

### Does JARVIS respect my privacy?
Absolutely. JARVIS processes audio filtering, file search, and app control locally on your machine. Your personal files remain private on your computer.

### Can JARVIS run offline?
Yes! JARVIS includes built-in support for offline local AI models (such as Ollama and local Whisper audio recognition).

---

## 🛠️ For Developers & Technical Users

If you want to inspect the architecture, build plugins, or contribute to the project:

- **System Architecture Blueprint**: Read the comprehensive [v2 Architecture Blueprint](br_architecture/README.md).
- **Automated Test Suite**: Run `python -m pytest tests/` to verify all **136 unit and integration tests**.
- **Plugin Platform**: Register custom tool handlers inside `tools/registry.py`.

---

## 📜 License

Distributed under the **MIT License**. Created by [bharthraj1412](https://github.com/bharthraj1412).
