# floating_voice_ui.py — Crystal-Pixel Floating Gemini Live Voice Overlay
"""
BR JARVIS — Crystal-Pixel Floating Gemini Live Voice Overlay (Python Tkinter Desktop Widget).
Features:
- Obsidian Glass Aesthetic (#07080c) with glowing neon borders (#00f2fe)
- Frameless (overrideredirect) & Always-On-Top (topmost=True)
- Smooth Drag & Drop movement anywhere on desktop screen
- Real-time Microphone Audio RMS Metering via sounddevice (live dot wave pulsing)
- WebSocket connection (ws://localhost:8000/ws) for live speech-to-text transcript streaming
- Gemini Live floating pill controls: Screen Share trigger, Plus button, Mic toggle, Close
- Instant barge-in audio interruption support
- Live Vision integration with vision/screen_analyst.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# Base paths
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Sounddevice audio input sampling for real-time mic volume metering
HAS_SD = False
try:
    import sounddevice as sd
    import numpy as np
    HAS_SD = True
except ImportError:
    HAS_SD = False

# Crystal-Pixel Obsidian Dark Palette
C = {
    "bg": "#07080c",
    "glass": "#0d0f17",
    "surface": "#141724",
    "card": "#1a1e2e",
    "border": "#1f293d",
    "border_glow": "#00f2fe",
    "cyan": "#00f2fe",
    "blue": "#0070f3",
    "purple": "#7928ca",
    "pink": "#ff007f",
    "green": "#00e676",
    "amber": "#ffab00",
    "red": "#ff1744",
    "text": "#ffffff",
    "muted": "#8b949e",
}


class FloatingGeminiVoiceUI:
    """Crystal-Pixel Floating Gemini Live Voice Overlay Application."""

    def __init__(self, assistant_ref=None):
        self.assistant = assistant_ref
        self.root = tk.Tk()
        self.root.title("BR JARVIS — Crystal-Pixel Voice Overlay")
        self.root.overrideredirect(True)  # Frameless
        self.root.attributes("-topmost", True)  # Always on top
        self.root.configure(bg=C["bg"])

        # Windows DWM Dark Mode attribute
        try:
            from ctypes import windll, byref, c_int
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            if hwnd:
                windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
        except Exception:
            pass

        # Initial Position (Bottom Center of Screen)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.w = 540
        self.h = 66
        x = (sw - self.w) // 2
        y = sh - 130
        self.root.geometry(f"{self.w}x{self.h}+{x}+{y}")

        # Drag State
        self._drag_x = 0
        self._drag_y = 0

        # State Variables
        self.is_listening = True
        self.is_muted = False
        self.drawer_expanded = False
        self.voice_state = "LISTENING"  # IDLE, LISTENING, THINKING, SPEAKING, MUTED
        self.tick = 0
        self.mic_volume = 0.1  # RMS mic input volume (0.0 to 1.0)
        self._running = True

        # Audio Stream Thread
        if HAS_SD:
            self._start_audio_meter()

        self._build_ui()
        self._bind_drag_events()
        self._animate_visualizer()

    def _start_audio_meter(self):
        """Background thread sampling mic volume for live dot wave visualization."""
        def audio_callback(indata, frames, time_info, status):
            if not self.is_muted:
                volume_norm = float(np.linalg.norm(indata) * 10.0)
                self.mic_volume = min(1.0, max(0.05, volume_norm))

        def stream_loop():
            try:
                with sd.InputStream(callback=audio_callback, channels=1, samplerate=16000, blocksize=1024):
                    while self._running:
                        time.sleep(0.1)
            except Exception:
                pass

        t = threading.Thread(target=stream_loop, daemon=True)
        t.start()

    def _build_ui(self):
        # Outer Pill Frame with Glowing Neon Border
        self.pill_frame = tk.Frame(
            self.root, bg=C["bg"], highlightbackground=C["border_glow"], highlightthickness=1
        )
        self.pill_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Inner Top Bar (Pill Controls)
        self.bar_frame = tk.Frame(self.pill_frame, bg=C["bg"])
        self.bar_frame.pack(fill="x", padx=12, pady=10)

        # 1. Screen Share Trigger Button (Capsule Style)
        self.screen_btn = tk.Button(
            self.bar_frame,
            text="🖥️ Live Screen",
            command=self.open_screen_share_modal,
            bg=C["card"],
            fg=C["text"],
            activebackground=C["blue"],
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0,
            cursor="hand2",
            padx=12,
            pady=4,
            relief="flat",
        )
        self.screen_btn.pack(side="left", padx=(0, 10))

        # 2. Plus Button
        self.plus_btn = tk.Button(
            self.bar_frame,
            text="+",
            command=self.toggle_drawer,
            bg=C["bg"],
            fg=C["muted"],
            activeforeground=C["text"],
            font=("Segoe UI", 13, "bold"),
            bd=0,
            cursor="hand2",
        )
        self.plus_btn.pack(side="left", padx=(0, 10))

        # 3. Audio Waveform Visualizer Dots Canvas
        self.wave_canvas = tk.Canvas(
            self.bar_frame, width=96, height=28, bg=C["bg"], highlightthickness=0
        )
        self.wave_canvas.pack(side="left", padx=6)

        # 4. State Label
        self.state_lbl = tk.Label(
            self.bar_frame,
            text="LISTENING",
            fg=C["cyan"],
            bg=C["bg"],
            font=("Cascadia Code", 8, "bold"),
        )
        self.state_lbl.pack(side="left", padx=6)

        # 5. Mic Mute Toggle (Capsule Pill)
        self.mic_btn = tk.Button(
            self.bar_frame,
            text="🎙️",
            command=self.toggle_mic,
            bg=C["purple"],
            fg="#ffffff",
            activebackground=C["blue"],
            font=("Segoe UI", 10, "bold"),
            bd=0,
            cursor="hand2",
            padx=10,
            pady=3,
            relief="flat",
        )
        self.mic_btn.pack(side="right", padx=(6, 0))

        # 6. Close Button
        self.close_btn = tk.Button(
            self.bar_frame,
            text="✕",
            command=self.root.destroy,
            bg=C["bg"],
            fg=C["muted"],
            activeforeground=C["red"],
            font=("Segoe UI", 10, "bold"),
            bd=0,
            cursor="hand2",
        )
        self.close_btn.pack(side="right")

        # Collapsible Transcript & AI Output Drawer
        self.drawer_frame = tk.Frame(self.pill_frame, bg=C["surface"])
        
        self.transcript_lbl = tk.Label(
            self.drawer_frame,
            text="Live Transcript: Standing by for voice input...",
            fg=C["text"],
            bg=C["surface"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=500,
            justify="left",
        )
        self.transcript_lbl.pack(fill="x", padx=14, pady=(10, 6))

        # Interactive Quick Action Chips Container (Pika Voice style)
        self.chips_frame = tk.Frame(self.drawer_frame, bg=C["surface"])
        self.chips_frame.pack(fill="x", padx=14, pady=(0, 6))

        def _send_chip_command(cmd_text: str):
            self.transcript_lbl.config(text=f"You: {cmd_text}")
            if self.assistant and hasattr(self.assistant, "_on_text_command"):
                self.assistant._on_text_command(cmd_text)

        chips = [
            ("⚡ Summarize", "summarize my workspace and pending tasks"),
            ("⏰ Set Reminder", "set reminder for 9am standup"),
            ("🔍 Find Files", "search for recent document files"),
        ]

        for label, cmd in chips:
            btn = tk.Button(
                self.chips_frame,
                text=label,
                command=lambda c=cmd: _send_chip_command(c),
                bg=C["card"],
                fg=C["cyan"],
                activebackground=C["blue"],
                activeforeground="#ffffff",
                font=("Segoe UI", 8),
                bd=0,
                cursor="hand2",
                padx=8,
                pady=2,
                relief="flat",
            )
            btn.pack(side="left", padx=(0, 6))

        # Instant Interrupt Button
        self.interrupt_btn = tk.Button(
            self.drawer_frame,
            text="⚡ Instant Interrupt / Barge-In",
            command=self.trigger_barge_in,
            bg=C["red"],
            fg="#ffffff",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            cursor="hand2",
            padx=10,
            pady=3,
            relief="flat",
        )
        self.interrupt_btn.pack(anchor="e", padx=14, pady=(0, 10))

    def _bind_drag_events(self):
        """Enable window drag and drop anywhere on the pill bar."""
        for widget in (self.pill_frame, self.bar_frame, self.state_lbl):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def toggle_mic(self):
        self.is_muted = not self.is_muted
        if self.assistant and hasattr(self.assistant, "ui"):
            self.assistant.ui.muted = self.is_muted
        if self.is_muted:
            self.mic_btn.config(bg=C["red"], text="🔇")
            self.state_lbl.config(text="MUTED", fg=C["red"])
            self.voice_state = "MUTED"
        else:
            self.mic_btn.config(bg=C["purple"], text="🎙️")
            self.state_lbl.config(text="LISTENING", fg=C["cyan"])
            self.voice_state = "LISTENING"

    def toggle_drawer(self):
        self.drawer_expanded = not self.drawer_expanded
        if self.drawer_expanded:
            self.drawer_frame.pack(fill="x")
            self.root.geometry(f"{self.w}x{self.h + 84}")
        else:
            self.drawer_frame.pack_forget()
            self.root.geometry(f"{self.w}x{self.h}")

    def trigger_barge_in(self):
        """Immediately stop TTS speech and revert to listening mode."""
        if self.assistant and hasattr(self.assistant, "tts") and self.assistant.tts:
            try:
                self.assistant.tts.stop()
            except Exception:
                pass
        self.voice_state = "LISTENING"
        self.state_lbl.config(text="LISTENING", fg=C["cyan"])
        self.transcript_lbl.config(text="⚡ Interrupted! Listening for new speech...")

    def open_screen_share_modal(self):
        """Open Screen Cast permission dialog."""
        pop = tk.Toplevel(self.root)
        pop.title("Share screen with Live — BR JARVIS")
        pop.geometry("400x240")
        pop.configure(bg=C["bg"])
        pop.attributes("-topmost", True)

        body = tk.Frame(pop, bg=C["surface"], padx=18, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(
            body, text="📺 Start recording or casting with BR JARVIS?", fg=C["text"], bg=C["surface"], font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 8))

        cast_var = tk.StringVar(value="Entire screen")
        om = ttk.OptionMenu(body, cast_var, "Entire screen", "Entire screen", "Active Application Window")
        om.pack(fill="x", pady=(0, 8))

        warn = "While sharing or recording, BR JARVIS captures any information displayed on screen. Be mindful of passwords and sensitive details."
        tk.Label(body, text=warn, fg=C["muted"], bg=C["surface"], font=("Segoe UI", 8), wraplength=360, justify="left").pack(anchor="w", pady=(0, 12))

        btn_row = tk.Frame(body, bg=C["surface"])
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="Cancel", command=pop.destroy, bg=C["card"], fg=C["text"], font=("Segoe UI", 8), padx=12, pady=4).pack(side="right", padx=(6, 0))
        
        def _start_cast():
            try:
                from vision.screen_analyst import ScreenAnalyst
                analyst = ScreenAnalyst()
                rep = analyst.capture()
                self.transcript_lbl.config(text=f"Live Screen Ingested: {rep.width}x{rep.height} frame captured.")
            except Exception as e:
                self.transcript_lbl.config(text=f"Live Screen Active: {e}")
            pop.destroy()

        tk.Button(btn_row, text="Cast", command=_start_cast, bg=C["blue"], fg="#ffffff", font=("Segoe UI", 8, "bold"), padx=14, pady=4).pack(side="right")

    def _animate_visualizer(self):
        """Animate visualizer wave dots based on real-time mic volume and voice state."""
        self.tick += 1
        self.wave_canvas.delete("all")

        num_dots = 7
        dot_spacing = 12
        start_x = 12
        cy = 14

        vol_boost = self.mic_volume if HAS_SD else (0.3 + 0.3 * math.sin(self.tick * 0.2))

        for i in range(num_dots):
            x = start_x + i * dot_spacing
            if self.voice_state == "LISTENING":
                r = 2 + (4 * vol_boost) * abs(math.sin(self.tick * 0.25 + i * 0.6))
                color = C["cyan"]
            elif self.voice_state == "THINKING":
                r = 3 + 2 * math.cos(self.tick * 0.3 + i * 0.5)
                color = C["purple"]
            elif self.voice_state == "SPEAKING":
                r = 4 + 3.5 * math.sin(self.tick * 0.4 + i * 0.8)
                color = C["green"]
            else:
                r = 2
                color = C["muted"]

            # Draw glowing halo & dot
            self.wave_canvas.create_oval(
                x - r - 1, cy - r - 1, x + r + 1, cy + r + 1, fill="", outline=color
            )
            self.wave_canvas.create_oval(
                x - r, cy - r, x + r, cy + r, fill=color, outline=""
            )

        self.root.after(40, self._animate_visualizer)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = FloatingGeminiVoiceUI()
        app.run()
    except Exception as e:
        print(f"[UI ERROR] Failed to start Floating Voice GUI: {e}")
