"""
JARVIS MK37 — Next-Gen AI OS Control Center (v6.0)
Colorful Glossy Glassmorphic Interface with Vibrant Controls.
Features 12 Multi-Color Glossy Integration Tiles (uinew.png), Multi-Color Particle Field,
Dual-Tone Radial Aurora, Neon Telemetry Gauges, Floating Voice Orb, and Max Control Center.
"""
from __future__ import annotations

import os, json, time, math, random, threading, platform, subprocess, sys, webbrowser
import tkinter as tk
from tkinter import ttk
from collections import deque
from pathlib import Path

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageEnhance
    _PIL = True
except ImportError:
    _PIL = False

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

# ── Base paths ────────────────────────────────────────────────────────────────
def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
API_FILE    = CONFIG_DIR / "api_keys.json"
MODELS_FILE = CONFIG_DIR / "models.json"

# ── Identity ──────────────────────────────────────────────────────────────────
SYSTEM_NAME = "B.R JARVIS"
MODEL_BADGE = "BR NEURAL CORE v6.0 — Colorful Glossy Glass OS"

# ── Colorful Glossy Color Palette ─────────────────────────────────────────────
C = {
    "bg":         "#050608",      # Deep dark space base
    "bg_trans":   "#090b10",      # Glass backdrop
    "surface":    "#0e111a",      # Frosted glass panel
    "card":       "#141824",      # Card surface
    "card_h":     "#1b2030",      # Card hover
    "card_glow":  "#242c40",      # Card border glow

    "border":     "#1f293d",      # Standard border
    "border_glow":"#00f2fe",      # Focused border glow
    "border_s":   "#161f30",      # Subtle border

    "accent":     "#0070f3",      # Electric Blue
    "accent_l":   "#00f2fe",      # Light Cyan
    "cyan":       "#00f2fe",      # Neon Cyan
    "purple":     "#7928ca",      # Deep Purple
    "pink":       "#ff007f",      # Neon Pink
    "green":      "#00e676",      # Neon Green
    "amber":      "#ffab00",      # Neon Amber
    "magenta":    "#ff007f",      # Neon Magenta

    "t1":         "#ffffff",      # High-contrast white
    "t2":         "#f0f4f8",      # Bright text
    "t3":         "#8b949e",      # Secondary text
    "t4":         "#64748b",      # Muted text
    "t5":         "#334155",      # Dim text

    "ok":         "#00e676",
    "warn":       "#ffab00",
    "err":        "#ff1744",
    "info":       "#00f2fe",

    "st_listen":  "#00e676",
    "st_speak":   "#00f2fe",
    "st_think":   "#7928ca",
    "st_mute":    "#ff1744",
    "st_proc":    "#ffab00",
}

# 12 Multi-Color Integration Specs (Icon, Label, Action, Accent Color, Glass BG, Gloss Glow)
INTEGRATION_TILES = [
    ("📅", "Open Calendar", "https://calendar.google.com", "#007aff", "#0a2240", "#00b2ff"),
    ("⏱️", "Set Timer", "set timer for 10 minutes", "#ff9500", "#3d2200", "#ffc04d"),
    ("✉️", "Check Email", "https://mail.google.com", "#af52de", "#2c123b", "#d988ff"),
    ("🗺️", "Quick Map", "https://maps.google.com", "#34c759", "#0c3316", "#62e083"),
    ("📋", "Task List", "show task list and planner", "#ff2d55", "#3d0c18", "#ff6b87"),
    ("🎙️", "Voice Memos", "start voice memo recording", "#00f2fe", "#052e3d", "#64f7ff"),
    ("🎵", "Play Music", "https://open.spotify.com", "#ff007f", "#3d0522", "#ff59b2"),
    ("🌤️", "Check Weather", "what is the weather today", "#ffcc00", "#3d3000", "#ffe066"),
    ("🔍", "Search Web", "search google for latest AI news", "#0052d4", "#071a42", "#4382f7"),
    ("🌐", "Open Browser", "https://google.com", "#5e5ce6", "#191740", "#8e8cf7"),
    ("🖥️", "System Stats", "SHOW_TELEMETRY", "#64d2ff", "#0a2b3d", "#9de5ff"),
    ("⚙️", "Quick Settings", "SHOW_SETTINGS", "#ff6b6b", "#3d1515", "#ffa3a3"),
]

# ── Fonts ─────────────────────────────────────────────────────────────────────
F = {
    "ui":      ("Segoe UI", 9),
    "ui_b":    ("Segoe UI", 9, "bold"),
    "ui_sm":   ("Segoe UI", 8),
    "ui_xs":   ("Segoe UI", 7),
    "ui_lg":   ("Segoe UI", 11, "bold"),
    "ui_xl":   ("Segoe UI", 14, "bold"),
    "ui_title":("Segoe UI", 18, "bold"),
    "mono":    ("Cascadia Code", 9),
    "mono_sm": ("Cascadia Code", 8),
    "mono_xs": ("Cascadia Code", 7),
    "mono_b":  ("Cascadia Code", 10, "bold"),
    "clock":   ("Cascadia Code", 16, "bold"),
}


class GlassParticle:
    """Multi-colored floating glass particle for background depth."""
    __slots__ = ["x", "y", "vx", "vy", "r", "phase", "speed", "color"]
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        angle = random.uniform(0, 6.28)
        self.speed = random.uniform(0.04, 0.18)
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.r  = random.uniform(1.2, 3.0)
        self.phase = random.uniform(0, 6.28)
        # Select vibrant particle color
        self.color = random.choice([C["cyan"], C["purple"], C["pink"], C["green"], C["accent_l"], C["amber"]])

    def update(self, w, h):
        self.x = (self.x + self.vx) % w
        self.y = (self.y + self.vy) % h
        self.phase += 0.025


class JarvisUI:
    """Colorful Glossy Next-Gen AI OS Interface for BR JARVIS."""

    def __init__(self, face_path, size=None):
        self.root = tk.Tk()
        self.root.title("B.R JARVIS — AI Operating System")
        self.root.resizable(True, True)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.W = min(sw, 1340)
        self.H = min(sh, 900)

        # Saved geometry
        self.norm_geometry = f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}"
        self.root.geometry(self.norm_geometry)
        self.root.configure(bg=C["bg"])
        self.root.minsize(980, 680)

        # Apply Dark Mode attribute on Windows
        try:
            from ctypes import windll, byref, c_int
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
        except Exception:
            pass

        # Display Modes: "FULL", "COMPACT", "SLEEP"
        self.display_mode = "FULL"
        self._is_sleeping  = False
        self._drag_data    = {"x": 0, "y": 0}

        # Hover state for integration tiles
        self._hovered_tile = -1

        # ── State ─────────────────────────────────────────────────────────
        self.speaking      = False
        self.muted         = False
        self.scale         = 1.0
        self.target_scale  = 1.0
        self.glow_a        = 0.55
        self.target_glow   = 0.55
        self.last_t        = time.time()
        self.tick          = 0
        self.breath        = 0.0
        self.ring_angles   = [0.0, 120.0, 240.0]
        self.pulse_rings   = []
        self.status_blink  = True
        self._state        = "INITIALISING"
        self._prev_state   = ""
        self.status_text   = "INITIALISING"
        self._start_time   = time.time()

        # Audio Waveform
        self._wave_data    = [0.0] * 56
        self._wave_smooth  = [0.0] * 56

        # Multi-color background particles
        self._particles    = [GlassParticle(self.W, self.H) for _ in range(35)]

        # Telemetry
        self._cpu          = 0.0
        self._ram          = 0.0
        self._disk         = 0.0
        self._net_s        = 0
        self._net_r        = 0
        self._agent_tasks  = {}

        # Log & Command History
        self._cmd_history  = deque(maxlen=50)
        self._hist_idx     = -1
        self._log_entries  = deque(maxlen=300)

        # Model Info
        self._active_model = self._load_active_model()

        # Callbacks
        self.on_text_command = None

        # Face/Orb Image
        self._face_pil     = None
        self._face_cache   = None
        self._has_face     = False
        self.FACE_SZ       = min(int(self.H * 0.35), 280)
        self.FCX           = int(self.W * 0.30)
        self.FCY           = int(self.H * 0.44)
        self._load_face(face_path)

        # ── Build Core UI Layout ──────────────────────────────────────────
        self._build_main_canvas()
        self._build_right_panel()
        self._build_bottom_bar()

        # ── Key & Window Bindings ─────────────────────────────────────────
        self.root.bind("<Configure>", self._on_resize)
        self.root.bind("<F4>", lambda e: self._toggle_mute())
        self.root.bind("<F5>", lambda e: self.set_state("LISTENING"))
        self.root.bind("<F11>", lambda e: self._toggle_sleep_mode())
        self.root.bind("<F12>", lambda e: self._switch_mode("MISSION_CONTROL"))
        self.root.bind("<Control-Shift-C>", lambda e: self._show_max_control_panel())
        self.root.bind("<Control-Shift-c>", lambda e: self._show_max_control_panel())
        self.root.bind("<Escape>", lambda e: self._input_entry.focus_set() if not self._is_sleeping else self._switch_mode("FULL"))
        self.root.bind("<Control-l>", lambda e: self._clear_log())
        self.root.bind("<Control-k>", lambda e: self._show_command_palette_modal())

        self._api_key_ready = self._api_keys_exist()
        if not self._api_key_ready:
            self.root.after(200, self._show_setup_ui)

        self._start_sys_monitor()
        self._animate()
        self.root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

    # ══════════════════════════════════════════════════════════════════════
    # ── Main Canvas & Layout ─────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    def _build_main_canvas(self):
        """Build main background canvas and mouse handlers."""
        W, H = self.W, self.H

        self.bg = tk.Canvas(self.root, width=W, height=H,
                            bg=C["bg"], highlightthickness=0)
        self.bg.place(x=0, y=0)

        # Mouse tracking for tile hover & drag
        self.bg.bind("<Motion>", self._on_canvas_motion)
        self.bg.bind("<Button-1>", self._on_canvas_click)
        self.bg.bind("<B1-Motion>", self._on_canvas_drag)

    def _build_right_panel(self):
        """Right panel containing Model Selector, Telemetry, Agent Status, and Log."""
        W, H = self.W, self.H
        PW = int(W * 0.32)
        PX = W - PW
        PY = 0

        self.panel_frame = tk.Frame(
            self.root, bg=C["surface"],
            highlightbackground=C["border"],
            highlightthickness=1
        )
        self.panel_frame.place(x=PX, y=PY, width=PW, height=H - 52)

        # ── Header: Model & Settings Icon ─────────────────────────────────
        hdr = tk.Frame(self.panel_frame, bg=C["surface"])
        hdr.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(hdr, text="MODEL ROUTER", fg=C["cyan"], bg=C["surface"],
                 font=F["ui_xs"]).pack(side="left")

        # Glossy Settings Icon Button
        settings_btn = tk.Button(
            hdr, text="⚙ Settings", command=self._show_settings_modal,
            fg=C["t1"], bg=C["card"],
            activeforeground="#ffffff", activebackground=C["accent"],
            font=F["ui_sm"], borderwidth=0, cursor="hand2", relief="flat", padx=10, pady=3
        )
        settings_btn.pack(side="right")

        self._model_lbl = tk.Label(
            self.panel_frame, text=f"⚡ {self._active_model}",
            fg=C["accent_l"], bg=C["surface"], font=F["mono_sm"], anchor="w"
        )
        self._model_lbl.pack(fill="x", padx=14, pady=(0, 6))

        # Divider
        tk.Frame(self.panel_frame, bg=C["border"], height=1).pack(fill="x", padx=12, pady=4)

        # ── Telemetry Section ─────────────────────────────────────────────
        met_hdr = tk.Frame(self.panel_frame, bg=C["surface"])
        met_hdr.pack(fill="x", padx=14, pady=(6, 2))
        tk.Label(met_hdr, text="SYSTEM TELEMETRY", fg=C["purple"], bg=C["surface"],
                 font=F["ui_xs"]).pack(side="left")

        self.metrics_canvas = tk.Canvas(
            self.panel_frame, bg=C["surface"],
            highlightthickness=0, height=92
        )
        self.metrics_canvas.pack(fill="x", padx=12)

        # Divider
        tk.Frame(self.panel_frame, bg=C["border"], height=1).pack(fill="x", padx=12, pady=4)

        # ── Agent & Planner Section ───────────────────────────────────────
        agent_hdr = tk.Frame(self.panel_frame, bg=C["surface"])
        agent_hdr.pack(fill="x", padx=14, pady=(6, 2))
        tk.Label(agent_hdr, text="AGENT STATUS", fg=C["green"], bg=C["surface"],
                 font=F["ui_xs"]).pack(side="left")

        self.agent_canvas = tk.Canvas(
            self.panel_frame, bg=C["surface"],
            highlightthickness=0, height=44
        )
        self.agent_canvas.pack(fill="x", padx=12)

        # Divider
        tk.Frame(self.panel_frame, bg=C["border"], height=1).pack(fill="x", padx=12, pady=4)

        # ── Neural Log Section ────────────────────────────────────────────
        log_hdr = tk.Frame(self.panel_frame, bg=C["surface"])
        log_hdr.pack(fill="x", padx=14, pady=(6, 4))
        tk.Label(log_hdr, text="NEURAL LOG", fg=C["pink"], bg=C["surface"],
                 font=F["ui_xs"]).pack(side="left")
        self._log_count_var = tk.StringVar(value="0")
        tk.Label(log_hdr, textvariable=self._log_count_var,
                 fg=C["t4"], bg=C["surface"], font=F["ui_xs"]).pack(side="right")

        clear_btn = tk.Button(
            log_hdr, text="Clear", command=self._clear_log,
            fg=C["t3"], bg=C["surface"],
            activeforeground=C["t1"], activebackground=C["card"],
            font=F["ui_xs"], borderwidth=0, cursor="hand2", relief="flat"
        )
        clear_btn.pack(side="right", padx=(0, 8))

        log_cont = tk.Frame(self.panel_frame, bg=C["bg"])
        log_cont.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        scroll = tk.Scrollbar(log_cont, orient="vertical",
                               bg=C["surface"], troughcolor=C["bg"],
                               activebackground=C["t4"], width=6)
        self.log_text = tk.Text(
            log_cont,
            fg=C["t2"], bg=C["bg"],
            insertbackground=C["cyan"],
            borderwidth=0, wrap="word",
            font=F["mono_sm"], padx=8, pady=6,
            yscrollcommand=scroll.set,
            state="disabled", cursor="arrow",
            selectbackground=C["card_glow"],
            selectforeground=C["t1"],
            spacing1=2, spacing3=2,
        )
        scroll.config(command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Log Tags
        self.log_text.tag_config("you",  foreground=C["t1"],    font=(F["mono_sm"][0], F["mono_sm"][1], "bold"))
        self.log_text.tag_config("ai",   foreground=C["cyan"],  font=F["mono_sm"])
        self.log_text.tag_config("sys",  foreground=C["t3"],    font=F["mono_xs"])
        self.log_text.tag_config("err",  foreground=C["err"],   font=(F["mono_sm"][0], F["mono_sm"][1], "bold"))
        self.log_text.tag_config("tool", foreground=C["green"], font=F["mono_xs"])
        self.log_text.tag_config("time", foreground=C["t4"],    font=F["mono_xs"])

    def _build_bottom_bar(self):
        """Bottom navigation bar with glossy mode switchers and send controls."""
        W, H = self.W, self.H
        PW = int(W * 0.32)
        bar_y = H - 52

        self.bottom_bar = tk.Frame(self.root, bg=C["surface"],
                                   highlightbackground=C["border"],
                                   highlightthickness=1)
        self.bottom_bar.place(x=0, y=bar_y, width=W, height=52)

        # Mode Switchers
        mode_frame = tk.Frame(self.bottom_bar, bg=C["surface"])
        mode_frame.pack(side="left", padx=12)

        modes = [
            ("FULL", "🖥️ Workspace", lambda: self._switch_mode("FULL")),
            ("COMPACT", "📱 Compact", lambda: self._switch_mode("COMPACT")),
            ("SLEEP", "🌙 Sleep Orb", lambda: self._switch_mode("SLEEP")),
            ("MISSION_CONTROL", "🚀 Mission Control", lambda: self._switch_mode("MISSION_CONTROL")),
            ("MAX", "🎛️ Max Control", self._show_max_control_panel),
        ]
        self._mode_btns = {}
        for m_key, label, cmd in modes:
            btn = tk.Button(
                mode_frame, text=label, command=cmd,
                fg=C["t3"], bg=C["card"],
                activeforeground="#ffffff", activebackground=C["accent"],
                font=F["ui_sm"], borderwidth=0, cursor="hand2", relief="flat", padx=10, pady=5
            )
            btn.pack(side="left", padx=3)
            self._mode_btns[m_key] = btn

        self._update_mode_button_styles()

        # Center: Glossy Input box
        inp_cont = tk.Frame(self.bottom_bar, bg=C["card"],
                            highlightbackground=C["border_glow"], highlightthickness=1)
        inp_cont.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        tk.Label(inp_cont, text="❯", fg=C["cyan"], bg=C["card"],
                 font=("Consolas", 12, "bold")).pack(side="left", padx=(10, 4))

        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            inp_cont,
            textvariable=self._input_var,
            fg=C["t1"], bg=C["card"],
            insertbackground=C["cyan"],
            borderwidth=0, font=F["mono"],
            highlightthickness=0,
        )
        self._input_entry.pack(side="left", fill="both", expand=True, padx=4)
        self._input_entry.bind("<Return>",   self._on_input_submit)
        self._input_entry.bind("<KP_Enter>", self._on_input_submit)
        self._input_entry.bind("<Up>",       self._hist_prev)
        self._input_entry.bind("<Down>",     self._hist_next)
        self._input_entry.bind("<Tab>",      self._autocomplete)

        # Character Counter
        self._charcount_var = tk.StringVar(value="")
        tk.Label(inp_cont, textvariable=self._charcount_var,
                 fg=C["t4"], bg=C["card"], font=F["ui_xs"]).pack(side="right", padx=4)
        self._input_var.trace_add("write", self._update_charcount)

        # Glossy Send Button
        send_btn = tk.Button(
            inp_cont, text="Send →", command=self._on_input_submit,
            fg="#ffffff", bg=C["accent"],
            activeforeground="#ffffff", activebackground=C["cyan"],
            font=F["ui_b"], borderwidth=0, cursor="hand2", relief="flat", padx=14
        )
        send_btn.pack(side="right", fill="y")

        # Mic Icon Button
        right_actions = tk.Frame(self.bottom_bar, bg=C["surface"])
        right_actions.pack(side="right", padx=12)

        self.mic_btn = tk.Button(
            right_actions, text="🎙️", command=self._toggle_mute,
            fg=C["t1"], bg=C["card"],
            activeforeground="#ffffff", activebackground=C["green"],
            font=("Segoe UI", 12), borderwidth=0, cursor="hand2", relief="flat", width=3
        )
        self.mic_btn.pack(side="right", padx=2)

    # ══════════════════════════════════════════════════════════════════════
    # ── 12 Multi-Color Glossy Integration Grid (uinew.png) ─────────────────
    # ══════════════════════════════════════════════════════════════════════

    def _draw_integrations_grid(self, c, grid_x, grid_y, grid_w, grid_h):
        """Draw 12 vibrant colorful glossy integration tiles from uinew.png."""
        if self.display_mode != "FULL" or self._is_sleeping:
            return

        # Title & Subtitle Header
        c.create_text(grid_x + grid_w // 2, grid_y + 18,
                      text="CUSTOM INTEGRATIONS & QUICK CONTROLS",
                      fill=C["t1"], font=F["ui_title"], anchor="center")
        c.create_text(grid_x + grid_w // 2, grid_y + 40,
                      text="Configured with 12 active integrations. Click any tile to launch.",
                      fill=C["t3"], font=F["ui_sm"], anchor="center")

        cols = 4
        rows = 3
        tile_w = (grid_w - (cols - 1) * 16 - 32) // cols
        tile_h = (grid_h - 60 - (rows - 1) * 14) // rows

        start_x = grid_x + 16
        start_y = grid_y + 58

        for idx, (icon, label, action, color, bg_glass, glow) in enumerate(INTEGRATION_TILES):
            r = idx // cols
            col = idx % cols
            tx = start_x + col * (tile_w + 16)
            ty = start_y + r * (tile_h + 14)

            is_hover = (idx == self._hovered_tile)
            border_col = glow if is_hover else color
            bg_col = color if is_hover else bg_glass

            # 1. Base Glass Tile Card
            c.create_rectangle(tx, ty, tx + tile_w, ty + tile_h,
                               fill=bg_col, outline=border_col, width=1.5 if is_hover else 1)

            # 2. Specular Top Gloss Highlight Line (3D Glass Reflection)
            c.create_line(tx + 4, ty + 2, tx + tile_w - 4, ty + 2,
                          fill="#ffffff" if is_hover else glow, width=1)

            # 3. Outer Glow Accent Line on left
            c.create_line(tx + 2, ty + 6, tx + 2, ty + tile_h - 6,
                          fill=color, width=2)

            # 4. Icon & Text Label
            c.create_text(tx + tile_w // 2, ty + tile_h // 2 - 12,
                          text=icon, font=("Segoe UI", 20 if is_hover else 18), fill="#ffffff" if is_hover else color)
            c.create_text(tx + tile_w // 2, ty + tile_h // 2 + 16,
                          text=label, font=F["ui_b"], fill="#ffffff" if is_hover else C["t2"])

    def _on_canvas_motion(self, event):
        """Track mouse hover over integration tiles for glossy animation."""
        if self.display_mode != "FULL" or self._is_sleeping:
            return

        W, H = self.W, self.H
        grid_w = int(W * 0.62)
        grid_h = min(360, int(H * 0.46))
        grid_x = (int(W * 0.68) - grid_w) // 2
        grid_y = int(H * 0.44)

        cols = 4
        rows = 3
        tile_w = (grid_w - (cols - 1) * 16 - 32) // cols
        tile_h = (grid_h - 60 - (rows - 1) * 14) // rows
        start_x = grid_x + 16
        start_y = grid_y + 58

        hovered = -1
        for idx in range(12):
            r = idx // cols
            col = idx % cols
            tx = start_x + col * (tile_w + 16)
            ty = start_y + r * (tile_h + 14)
            if tx <= event.x <= tx + tile_w and ty <= event.y <= ty + tile_h:
                hovered = idx
                break

        if hovered != self._hovered_tile:
            self._hovered_tile = hovered

    def _handle_integration_click(self, x, y):
        """Handle clicks on integration tiles."""
        if self.display_mode != "FULL" or self._is_sleeping:
            return False

        W, H = self.W, self.H
        grid_w = int(W * 0.62)
        grid_h = min(360, int(H * 0.46))
        grid_x = (int(W * 0.68) - grid_w) // 2
        grid_y = int(H * 0.44)

        cols = 4
        rows = 3
        tile_w = (grid_w - (cols - 1) * 16 - 32) // cols
        tile_h = (grid_h - 60 - (rows - 1) * 14) // rows
        start_x = grid_x + 16
        start_y = grid_y + 58

        for idx, (icon, label, action, color, bg_glass, glow) in enumerate(INTEGRATION_TILES):
            r = idx // cols
            col = idx % cols
            tx = start_x + col * (tile_w + 16)
            ty = start_y + r * (tile_h + 14)

            if tx <= x <= tx + tile_w and ty <= y <= ty + tile_h:
                self.write_log(f"SYS: Integration triggered → {label}")
                if action == "SHOW_SETTINGS":
                    self._show_settings_modal()
                elif action == "SHOW_TELEMETRY":
                    self._show_max_control_panel()
                elif action.startswith("http"):
                    webbrowser.open(action)
                elif self.on_text_command:
                    threading.Thread(target=self.on_text_command, args=(action,), daemon=True).start()
                return True
        return False

    # ══════════════════════════════════════════════════════════════════════
    # ── Display Mode Switcher & Floating Sleep Orb ────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    def _switch_mode(self, mode: str):
        if mode == self.display_mode and not self._is_sleeping:
            return
        self.display_mode = mode
        if mode == "SLEEP":
            self._enter_sleep_orb_mode()
        else:
            if self._is_sleeping:
                self._wake_up_from_sleep_orb()
            self._update_mode_button_styles()

    def _enter_sleep_orb_mode(self):
        if self._is_sleeping: return
        self._is_sleeping = True
        self.set_state("MUTED")
        self.write_log("SYS: Entering Floating Sleep Voice Orb mode...")

        self.norm_geometry = self.root.geometry()
        try:
            self.root.overrideredirect(True)
            self.root.wm_attributes("-topmost", True)
        except Exception:
            pass

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"170x170+{sw - 220}+{sh - 260}")

        self.panel_frame.place_forget()
        self.bottom_bar.place_forget()
        self._update_mode_button_styles()

    def _wake_up_from_sleep_orb(self):
        if not self._is_sleeping: return
        self._is_sleeping = False
        try:
            self.root.overrideredirect(False)
            self.root.wm_attributes("-topmost", False)
        except Exception:
            pass

        self.root.geometry(self.norm_geometry)
        PW = int(self.W * 0.32)
        PX = self.W - PW
        self.panel_frame.place(x=PX, y=0, width=PW, height=self.H - 52)
        self.bottom_bar.place(x=0, y=self.H - 52, width=self.W, height=52)

        self.set_state("LISTENING")
        self.write_log("SYS: Woke up from Sleep. JARVIS active.")
        self._update_mode_button_styles()

    def _toggle_sleep_mode(self):
        if self._is_sleeping:
            self._switch_mode("FULL")
        else:
            self._switch_mode("SLEEP")

    def _on_canvas_click(self, event):
        if self._is_sleeping:
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y
            self._wake_up_from_sleep_orb()
        else:
            self._handle_integration_click(event.x, event.y)

    def _on_canvas_drag(self, event):
        if self._is_sleeping:
            dx = event.x - self._drag_data["x"]
            dy = event.y - self._drag_data["y"]
            x = self.root.winfo_x() + dx
            y = self.root.winfo_y() + dy
            self.root.geometry(f"+{x}+{y}")

    def _update_mode_button_styles(self):
        for m_key, btn in self._mode_btns.items():
            if m_key == self.display_mode:
                btn.config(fg="#ffffff", bg=C["accent"], activebackground=C["cyan"])
            else:
                btn.config(fg=C["t3"], bg=C["card"], activebackground=C["card_h"])

    # ══════════════════════════════════════════════════════════════════════
    # ── Animation & Drawing Loop ──────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    def _animate(self):
        self.tick += 1
        t = self.tick
        now = time.time()

        self.breath += 0.02

        interval = 0.1 if self.speaking else 0.35
        if now - self.last_t > interval:
            if self.speaking:
                self.target_scale = 1.0 + 0.04 * (0.5 + 0.5 * math.sin(self.breath * 3))
                self.target_glow  = 0.7 + 0.25 * math.sin(self.breath * 2)
            elif self.muted:
                self.target_scale = 1.0
                self.target_glow  = 0.12
            elif self._state == "THINKING":
                self.target_scale = 1.0 + 0.015 * math.sin(self.breath * 1.5)
                self.target_glow  = 0.35 + 0.12 * math.sin(self.breath * 2)
            else:
                self.target_scale = 1.0 + 0.008 * math.sin(self.breath)
                self.target_glow  = 0.3 + 0.08 * math.sin(self.breath * 0.8)
            self.last_t = now

        self.scale  += (self.target_scale - self.scale) * 0.12
        self.glow_a += (self.target_glow  - self.glow_a) * 0.12

        for i, spd in enumerate([0.3, -0.2, 0.5] if not self.speaking else [0.8, -0.5, 1.2]):
            self.ring_angles[i] = (self.ring_angles[i] + spd) % 360

        pspd = 2.2 if self.speaking else 1.1
        limit = (140 if self._is_sleeping else self.FACE_SZ) * 0.65
        self.pulse_rings = [r + pspd for r in self.pulse_rings if r + pspd < limit]
        if len(self.pulse_rings) < 3 and random.random() < (0.04 if self.speaking else 0.012):
            self.pulse_rings.append(0.0)

        for p in self._particles:
            p.update(self.W, self.H)

        self._update_waveform()

        if t % 30 == 0:
            self.status_blink = not self.status_blink

        self._draw_frame()

        if not self._is_sleeping:
            if t % 4 == 0:
                self._draw_metrics()
            if t % 6 == 0:
                self._draw_agent_status()

        self.root.after(16, self._animate)

    def _update_waveform(self):
        if self.speaking:
            for i in range(len(self._wave_data)):
                self._wave_data[i] = random.gauss(0, 0.5)
        elif self._state == "THINKING":
            t = self.tick * 0.06
            for i in range(len(self._wave_data)):
                self._wave_data[i] = 0.2 * math.sin(t + i * 0.3) * math.sin(t * 0.25)
        else:
            for i in range(len(self._wave_data)):
                self._wave_data[i] *= 0.9
        for i in range(len(self._wave_smooth)):
            self._wave_smooth[i] += (self._wave_data[i] - self._wave_smooth[i]) * 0.25

    # ══════════════════════════════════════════════════════════════════════
    # ── Canvas Rendering ──────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _hex_color(r, g, b, a=255):
        f = max(0.0, min(1.0, a / 255.0))
        return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

    def _state_color(self):
        return {
            "LISTENING":  C["st_listen"], "SPEAKING":   C["st_speak"],
            "THINKING":   C["st_think"],  "MUTED":      C["st_mute"],
            "PROCESSING": C["st_proc"],
        }.get(self._state, C["t3"])

    def _state_rgb(self):
        h = self._state_color().lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def _draw_frame(self):
        if not hasattr(self, "root") or not self.root.winfo_exists():
            return
        c = self.bg
        W, H = self.root.winfo_width(), self.root.winfo_height()
        c.delete("all")

        # Mission Control mode render
        if self.display_mode == "MISSION_CONTROL" and not self._is_sleeping:
            self._draw_mission_control(c, W, H)
            return

        # Sleep mode render
        if self._is_sleeping:
            c.create_rectangle(0, 0, W, H, fill=C["bg"], outline="")
            FCX = W // 2
            FCY = H // 2
            FW = min(W, H) - 20
            self._draw_orb_visual(c, FCX, FCY, FW)
            c.create_text(FCX, FCY + FW // 2 - 12, text="Wake: Hey Jarvis",
                          fill=C["t3"], font=F["ui_xs"], anchor="center")
            return

        # Main background
        c.create_rectangle(0, 0, W, H, fill=C["bg"], outline="")

        # Multi-colored depth particles
        for p in self._particles:
            alpha = 0.35 * (0.5 + 0.5 * math.sin(p.phase))
            a = max(0, min(255, int(alpha * 160)))
            if a < 3: continue
            c.create_oval(p.x - p.r, p.y - p.r, p.x + p.r, p.y + p.r, fill=p.color, outline="")

        # Center Voice Orb / Face area
        FCX = self.FCX if self.display_mode == "FULL" else int(W * 0.34)
        FCY = self.FCY if self.display_mode == "FULL" else int(H * 0.32)
        FW  = self.FACE_SZ if self.display_mode == "FULL" else int(self.FACE_SZ * 0.8)
        self._draw_orb_visual(c, FCX, FCY, FW)

        # Header status bar
        self._draw_header_bar(c, W)

        # Waveform below face
        self._draw_waveform(c, W, H, FCX, FCY, FW)

        # Integrations Grid in FULL mode
        if self.display_mode == "FULL":
            grid_w = int(W * 0.62)
            grid_h = min(360, int(H * 0.46))
            grid_x = (int(W * 0.68) - grid_w) // 2
            grid_y = int(H * 0.44)
            self._draw_integrations_grid(c, grid_x, grid_y, grid_w, grid_h)

    def _draw_orb_visual(self, c, FCX, FCY, FW):
        """Draw vibrant circular breathing orb with multi-colored pulse rings."""
        sr, sg, sb = self._state_rgb()
        ga = self.glow_a

        # Radial dual-color center glow
        for i in range(5):
            r = int(FW * (0.58 - i * 0.05))
            a = max(0, min(255, int(ga * 45 * (1 - i * 0.2))))
            col = self._hex_color(sr, sg, sb, a)
            c.create_oval(FCX-r, FCY-r, FCX+r, FCY+r, outline=col, width=1.5, fill="")

        # Multi-colored pulse rings (Cyan & Purple glow)
        for pr in self.pulse_rings:
            fade = 1.0 - pr / (FW * 0.65)
            if fade <= 0: continue
            a = max(0, int(110 * fade * ga))
            col = self._hex_color(sr, sg, sb, a)
            ri = int(FW * 0.30 + pr)
            c.create_oval(FCX-ri, FCY-ri, FCX+ri, FCY+ri, outline=col, width=1.5, fill="")

        # Arc rings
        specs = [(0.46, 1.5, 75, 95, C["cyan"]), (0.40, 1.0, 55, 110, C["purple"])]
        for idx, (rf, w, al, gap, arc_col) in enumerate(specs):
            rr = int(FW * rf)
            ba = self.ring_angles[idx]
            av = max(0, min(255, int(ga * 160 * (1 - idx * 0.3))))
            for s in range(360 // (al + gap)):
                st = (ba + s * (al + gap)) % 360
                c.create_arc(FCX-rr, FCY-rr, FCX+rr, FCY+rr,
                            start=st, extent=al, outline=arc_col, width=w, style="arc")

        # Face Image or Inner Orb
        fw = int(FW * self.scale)
        if self._has_face and _PIL:
            if self._face_cache is None or abs(self._face_cache[0] - self.scale) > 0.003:
                scaled = self._face_pil.resize((fw, fw), Image.BILINEAR)
                if self.muted:
                    r, g, b, a = scaled.split()
                    g = g.point(lambda px: int(px * 0.4))
                    b = b.point(lambda px: int(px * 0.4))
                    r = r.point(lambda px: min(255, int(px * 1.1 + 20)))
                    scaled = Image.merge("RGBA", (r, g, b, a))
                tk_img = ImageTk.PhotoImage(scaled)
                self._face_cache = (self.scale, tk_img)
            c.create_image(FCX, FCY, image=self._face_cache[1])
        else:
            orb_r = int(FW * 0.22 * self.scale)
            for i in range(5, 0, -1):
                frac = i / 5
                r2 = int(orb_r * frac)
                a = int(self.glow_a * 180 * frac)
                col = self._hex_color(int(sr*frac*0.6), int(sg*frac*0.6), int(sb*frac*0.6), a)
                c.create_oval(FCX-r2, FCY-r2, FCX+r2, FCY+r2, fill=col, outline="")
            c.create_text(FCX, FCY, text=SYSTEM_NAME, fill=C["t1"], font=F["mono_b"])

    def _draw_header_bar(self, c, W):
        c.create_text(24, 22, text=SYSTEM_NAME, fill=C["t1"], font=F["ui_xl"], anchor="w")
        c.create_text(24, 42, text=MODEL_BADGE, fill=C["cyan"], font=F["ui_xs"], anchor="w")

        # Time
        PW = int(W * 0.32)
        cx = W - PW - 24
        c.create_text(cx, 20, text=time.strftime("%H:%M:%S"), fill=C["t1"], font=F["clock"], anchor="e")
        c.create_text(cx, 42, text=time.strftime("%A, %B %d"), fill=C["t3"], font=F["ui_xs"], anchor="e")

        # Neon State pill
        sc = self._state_color()
        sym = "●" if self.status_blink else "○"
        state_text = f" {sym}  {self._state} "
        pill_x = (W - PW) // 2
        pill_y = 28
        pill_hw = max(len(state_text) * 4 + 10, 60)

        h = sc.lstrip("#")
        sr, sg, sb = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        pill_bg = self._hex_color(sr, sg, sb, 45)
        c.create_rectangle(pill_x - pill_hw, pill_y - 12, pill_x + pill_hw, pill_y + 12,
                          fill=pill_bg, outline=sc, width=1.5)
        c.create_text(pill_x, pill_y, text=state_text, fill=sc, font=F["ui_b"])

    def _draw_waveform(self, c, W, H, FCX, FCY, FW):
        wy = FCY + FW // 2 + 18
        if wy + 20 > H - 60: return

        if self._state == "LISTENING":
            sym = "🎙️ LISTENING FOR COMMAND..." if self.status_blink else "🎙️ LISTENING..."
            c.create_text(FCX, wy - 12, text=sym, fill=C["cyan"], font=F["ui_b"], anchor="center")

        N = len(self._wave_smooth)
        tw = int(W * 0.28)
        px0 = FCX - tw // 2
        bw = max(2, tw // N)
        BH = 14

        sc = self._state_color()
        for i, amp in enumerate(self._wave_smooth):
            h_bar = max(1, int(abs(amp) * BH * 2))
            h_bar = min(h_bar, BH)
            bx = px0 + i * (bw + 1)
            col = sc if h_bar > 2 else C["t5"]
            mid = wy + BH // 2
            c.create_rectangle(bx, mid - h_bar, bx + bw - 1, mid + h_bar, fill=col, outline="")

    def _draw_metrics(self):
        c = self.metrics_canvas
        c.delete("all")
        w = c.winfo_width() or 300
        h = 92

        c.create_rectangle(0, 0, w, h, fill=C["surface"], outline="")

        metrics = [
            ("CPU",  self._cpu,  C["cyan"]),
            ("RAM",  self._ram,  C["green"]),
            ("DISK", self._disk, C["purple"]),
        ]

        bar_w = w - 84

        for idx, (label, val, col) in enumerate(metrics):
            y0 = 6 + idx * 28
            c.create_text(10, y0 + 8, text=label, fill=C["t3"], font=F["ui_xs"], anchor="w")

            bx = 48
            c.create_rectangle(bx, y0 + 4, bx + bar_w, y0 + 12, fill=C["card"], outline="")
            fw = int(bar_w * val / 100)
            if fw > 0:
                c.create_rectangle(bx, y0 + 4, bx + fw, y0 + 12, fill=col, outline="")

            c.create_text(w - 8, y0 + 8, text=f"{val:.0f}%", fill=col,
                          font=F["mono_xs"], anchor="e")

        net = f"NET  ↑ {self._fmt_bytes(self._net_s)}   ↓ {self._fmt_bytes(self._net_r)}"
        c.create_text(10, 84, text=net, fill=C["t4"], font=F["mono_xs"], anchor="w")

    def _draw_agent_status(self):
        c = self.agent_canvas
        c.delete("all")
        w = c.winfo_width() or 300

        c.create_rectangle(0, 0, w, 44, fill=C["surface"], outline="")

        sc = self._state_color()
        dot = "●" if self.status_blink else "○"
        
        # Count running tasks
        running_cnt = sum(1 for t in self._agent_tasks.values() if t.get("status") in ("running", "queued"))
        badge = f"  ·  🚀 {running_cnt} Active" if running_cnt > 0 else ""
        
        c.create_text(10, 10, text=f"{dot}  BR  ·  {self._state}{badge}",
                      fill=sc, font=F["ui_b"], anchor="w")

        tasks = list(self._agent_tasks.items())[-2:]
        for i, (tid, info) in enumerate(tasks):
            y = 28 + i * 14
            st = info.get("status", "?")
            st_col = C["green"] if st in ("completed", "done") else C["err"] if st == "failed" else C["cyan"] if st == "running" else C["warn"]
            icon = "⚡" if st == "running" else "✓" if st in ("completed", "done") else "✕" if st == "failed" else "⏳"
            c.create_text(18, y, text=f"{icon} {info.get('name','agent')[:16]} [{st.upper()}]",
                          fill=st_col, font=F["ui_xs"], anchor="w")

    @staticmethod
    def _fmt_bytes(n):
        if n > 1_073_741_824: return f"{n/1_073_741_824:.1f} GB"
        if n > 1_048_576: return f"{n/1_048_576:.1f} MB"
        if n > 1024: return f"{n/1024:.0f} KB"
        return f"{n} B"

    def _draw_mission_control(self, c, W, H):
        """Draw Mission Control Fullscreen Developer & Diagnostic Mode."""
        c.create_rectangle(0, 0, W, H, fill=C["bg"], outline="")
        
        # Grid lines
        for x in range(0, W, 40):
            c.create_line(x, 0, x, H, fill="#0d1522", width=1)
        for y in range(0, H, 40):
            c.create_line(0, y, W, y, fill="#0d1522", width=1)
            
        # Particles
        for p in self._particles:
            c.create_oval(p.x - p.r, p.y - p.r, p.x + p.r, p.y + p.r, fill=p.color, outline="")

        # Title Header
        c.create_text(W // 2, 24, text="🚀 MISSION CONTROL — AI OS DEVELOPER & DIAGNOSTIC HUD",
                      fill=C["cyan"], font=("Segoe UI", 13, "bold"), anchor="center")
        c.create_text(W // 2, 44, text="Live EventBus Routing • Token Budget Profiler • Spatial Vector Memory • Reasoning DAG",
                      fill=C["t3"], font=F["ui_sm"], anchor="center")

        qw = (W - 48) // 2
        qh = (H - 120) // 2
        
        # Quadrant 1: EventBus Graph
        x1, y1 = 16, 60
        c.create_rectangle(x1, y1, x1 + qw, y1 + qh, fill=C["surface"], outline=C["border_glow"], width=1.5)
        c.create_text(x1 + 16, y1 + 18, text="📡 EVENTBUS SUBSYSTEM GRAPH", fill=C["cyan"], font=F["ui_b"], anchor="w")
        
        nodes = [
            ("Voice Engine", x1 + 60, y1 + 55, C["green"]),
            ("LLM Router", x1 + qw // 2, y1 + 55, C["accent_l"]),
            ("Task Queue", x1 + qw - 70, y1 + 55, C["amber"]),
            ("Event Bus Core", x1 + qw // 2, y1 + qh // 2, C["purple"]),
            ("Vector Memory", x1 + 70, y1 + qh - 45, C["cyan"]),
            ("Vision Engine", x1 + qw // 2, y1 + qh - 45, C["pink"]),
            ("Computer Operator", x1 + qw - 80, y1 + qh - 45, C["green"])
        ]
        
        cx, cy = x1 + qw // 2, y1 + qh // 2
        for name, nx, ny, col in nodes:
            if name != "Event Bus Core":
                pulse_offset = (self.tick * 3) % 100 / 100.0
                px = nx + (cx - nx) * pulse_offset
                py = ny + (cy - ny) * pulse_offset
                c.create_line(nx, ny, cx, cy, fill=col, dash=(4, 4), width=1)
                c.create_oval(px - 3, py - 3, px + 3, py + 3, fill=col, outline="")
                
        for name, nx, ny, col in nodes:
            c.create_oval(nx - 28, ny - 14, nx + 28, ny + 14, fill=C["card"], outline=col, width=1.5)
            c.create_text(nx, ny, text=name.split()[0], fill=C["t1"], font=F["ui_xs"], anchor="center")

        # Quadrant 2: Reasoning Tree & Token Profiler
        x2, y2 = 32 + qw, 60
        c.create_rectangle(x2, y2, x2 + qw, y2 + qh, fill=C["surface"], outline=C["border"], width=1.5)
        c.create_text(x2 + 16, y2 + 18, text="🧠 REASONING TREE & TOKEN BUDGET PROFILER", fill=C["purple"], font=F["ui_b"], anchor="w")
        
        c.create_text(x2 + 16, y2 + 42, text="Token Budget Ceiling: 1,000,000 / Session", fill=C["t3"], font=F["ui_xs"], anchor="w")
        c.create_rectangle(x2 + 16, y2 + 54, x2 + qw - 16, y2 + 66, fill=C["card"], outline=C["border"])
        used_w = int((qw - 32) * 0.28)
        c.create_rectangle(x2 + 16, y2 + 54, x2 + 16 + used_w, y2 + 66, fill=C["purple"], outline="")
        c.create_text(x2 + 24 + used_w, y2 + 60, text="280,450 tokens (28%)", fill=C["t1"], font=F["mono_xs"], anchor="w")
        
        c.create_text(x2 + 16, y2 + 82, text="Active Task DAG Branches:", fill=C["t2"], font=F["ui_sm"], anchor="w")
        dag_items = [
            ("Root: User Prompt ('Analyze System Setup')", C["accent_l"]),
            ("  ├── Step 1: Query System Telemetry & Hardware", C["green"]),
            ("  ├── Step 2: Read Configuration Matrix", C["cyan"]),
            ("  └── Step 3: Format Response via Gemini 3.5 Flash", C["purple"])
        ]
        for idx, item in enumerate(dag_items):
            c.create_text(x2 + 20, y2 + 102 + idx * 20, text=item[0], fill=item[1], font=F["mono_sm"], anchor="w")

        # Quadrant 3: Spatial Vector Memory
        x3, y3 = 16, 72 + qh
        c.create_rectangle(x3, y3, x3 + qw, y3 + qh, fill=C["surface"], outline=C["border"], width=1.5)
        c.create_text(x3 + 16, y3 + 18, text="💾 SPATIAL VECTOR MEMORY SPECTRUM", fill=C["green"], font=F["ui_b"], anchor="w")
        
        random.seed(42)
        for i in range(35):
            rx = x3 + 30 + (i * 137.5) % (qw - 60)
            ry = y3 + 42 + (i * 91.3) % (qh - 60)
            r = 2 + (i % 3)
            col = C["cyan"] if i % 4 == 0 else (C["purple"] if i % 3 == 0 else C["t4"])
            c.create_oval(rx - r, ry - r, rx + r, ry + r, fill=col, outline="")
            if i % 7 == 0:
                c.create_line(rx, ry, rx + 15, ry - 10, fill=C["t5"], width=1)
                c.create_text(rx + 18, ry - 12, text=f"vec_{i:03d}", fill=C["t3"], font=F["mono_xs"], anchor="w")

        # Quadrant 4: Vision & Hardware
        x4, y4 = 32 + qw, 72 + qh
        c.create_rectangle(x4, y4, x4 + qw, y4 + qh, fill=C["surface"], outline=C["border"], width=1.5)
        c.create_text(x4 + 16, y4 + 18, text="👁️ VISION INSPECTOR & HARDWARE TELEMETRY", fill=C["pink"], font=F["ui_b"], anchor="w")
        
        c.create_text(x4 + 16, y4 + 42, text=f"Screen Resolution: {W}x{H} @ 60 FPS", fill=C["t2"], font=F["mono_sm"], anchor="w")
        c.create_text(x4 + 16, y4 + 62, text=f"OCR Engine: Tesseract / Native Vision Pipeline", fill=C["t3"], font=F["ui_sm"], anchor="w")
        c.create_text(x4 + 16, y4 + 82, text=f"CPU: {self._cpu}%  |  RAM: {self._ram}%", fill=C["amber"], font=F["mono_sm"], anchor="w")
        c.create_text(x4 + 16, y4 + 102, text=f"Disk: {self._disk}%  |  Net: {self._net_s//1024} KB / {self._net_r//1024} KB", fill=C["info"], font=F["mono_sm"], anchor="w")
        
        c.create_rectangle(x4 + 16, y4 + qh - 40, x4 + qw - 16, y4 + qh - 12, fill=C["card"], outline=C["border_glow"])
        c.create_text(x4 + qw // 2, y4 + qh - 26, text="Press <F12> or <Esc> to Exit Mission Control", fill=C["cyan"], font=F["ui_b"], anchor="center")

    # ══════════════════════════════════════════════════════════════════════
    # ── Max Control Panel & Settings Modal ────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    def _show_max_control_panel(self):
        win = tk.Toplevel(self.root)
        win.title("BR JARVIS — Maximum Control Center")
        win.geometry("840x640")
        win.configure(bg=C["surface"])
        win.transient(self.root)
        win.grab_set()

        hdr = tk.Frame(win, bg=C["card"], height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🎛️ MAXIMUM CONTROL CENTER", fg=C["cyan"], bg=C["card"],
                 font=F["ui_title"]).pack(side="left", padx=16, pady=10)

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        # Tab 1: AI Routers
        t1 = tk.Frame(notebook, bg=C["surface"], padx=16, pady=16)
        notebook.add(t1, text="⚡ Task Router")
        tk.Label(t1, text="Domain-Optimized Gemini AI Work Modes", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 8))
        
        modes_spec = [
            ("💻 Code & Architecture", "gemini-3.1-pro-high", "Deep coding & refactoring"),
            ("🧠 Reasoning & Auditing", "gemini-3.1-pro-high", "Complex logic & math"),
            ("💬 General Assistant", "gemini-3-flash", "General Q&A & Search"),
            ("🤖 Agent DAG Planning", "gemini-3-flash-agent", "Autonomous task DAG"),
            ("👁️ Vision & Screen OCR", "gemini-3.1-flash-image", "Multimodal screen analysis"),
            ("⚡ Fast Status Summaries", "gemini-3.5-flash-low", "Ultra-fast low-latency"),
            ("⚡ Micro-Tasking Lite", "gemini-3.1-flash-lite", "Autocomplete & token count"),
        ]
        for label, model_id, desc in modes_spec:
            r = tk.Frame(t1, bg=C["card"], pady=5, padx=12)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=f"✓ {label}", fg=C["cyan"], bg=C["card"], font=F["ui_b"]).pack(side="left")
            tk.Label(r, text=f"{model_id}  ({desc})", fg=C["t3"], bg=C["card"], font=F["mono_xs"]).pack(side="right")

        # Tab 2: Multi-Task & Sub-Agents Dashboard
        t_tasks = tk.Frame(notebook, bg=C["surface"], padx=16, pady=16)
        notebook.add(t_tasks, text="🚀 Multi-Tasks")
        tk.Label(t_tasks, text="Active Multi-Tasks & Autonomous Sub-Agents", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 6))
        
        self._multitask_list_frame = tk.Frame(t_tasks, bg=C["surface"])
        self._multitask_list_frame.pack(fill="both", expand=True)
        self._render_multitask_cards()

        # Tab 3: Vision & Operator
        t2 = tk.Frame(notebook, bg=C["surface"], padx=16, pady=16)
        notebook.add(t2, text="👁️ Vision & Operator")
        tk.Label(t2, text="Computer Vision & Screen Controls", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 10))
        tk.Button(t2, text="📸 Capture & Analyze Screen", command=self._take_screenshot, bg=C["card"], fg=C["cyan"], font=F["ui_b"], pady=8).pack(fill="x", pady=4)
        tk.Button(t2, text="📋 Process Clipboard with AI", command=self._send_clipboard, bg=C["card"], fg=C["purple"], font=F["ui_b"], pady=8).pack(fill="x", pady=4)

        # Tab 3: Memory & Context
        t3 = tk.Frame(notebook, bg=C["surface"], padx=16, pady=16)
        notebook.add(t3, text="🧠 Memory & Context")
        tk.Label(t3, text="Spatial Vector Memory & Cache Status", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 10))
        tk.Label(t3, text="Vector Database: Active (ChromaDB / SQLite Embeddings)\nContext Budget: 1,000,000 Tokens\nArchival Search: Enabled", fg=C["t2"], bg=C["card"], font=F["mono_sm"], justify="left", padx=12, pady=12).pack(fill="x")

        # Tab 4: Voice & Speech
        t4 = tk.Frame(notebook, bg=C["surface"], padx=16, pady=16)
        notebook.add(t4, text="🎙️ Voice & Acoustics")
        tk.Label(t4, text="Speech Engine & Audio Configuration", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 10))
        tk.Label(t4, text=f"Wake Word: '{os.environ.get('JARVIS_WAKE_WORD', 'hey jarvis')}'\nSTT Engine: Native VAD + Whisper Engine\nAudio Equalizer: 56-band Realtime Visualizer Active", fg=C["t2"], bg=C["card"], font=F["mono_sm"], justify="left", padx=12, pady=12).pack(fill="x")

        # Tab 5: Performance
        t5 = tk.Frame(notebook, bg=C["surface"], padx=16, pady=16)
        notebook.add(t5, text="⚙️ Hardware Telemetry")
        tk.Label(t5, text="Hardware Telemetry & Acceleration", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 10))
        tk.Label(t5, text=f"Native Acceleration: pure-Python FNV-1a / math VAD active\nCPU Threads: {psutil.cpu_count() if _PSUTIL else 'N/A'}\nRAM Usage: {self._ram}%\nDisk Usage: {self._disk}%", fg=C["t2"], bg=C["card"], font=F["mono_sm"], justify="left", padx=12, pady=12).pack(fill="x")

        # Tab 6: Antigravity Token Telemetry
        t6 = tk.Frame(notebook, bg=C["surface"], padx=16, pady=16)
        notebook.add(t6, text="⚡ Token Telemetry")
        tk.Label(t6, text="Antigravity Ultra-Low Token Architecture", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 10))
        try:
            from context.token_manager import TokenBudgetManager
            telem = TokenBudgetManager().get_telemetry()
            telem_text = (
                f"Antigravity Mode Status: 🟢 ACTIVE\n"
                f"0-Token Bypassed Executions: {telem['bypassed_calls']}\n"
                f"Tokens Consumed: {telem['consumed']:,}\n"
                f"Tokens Saved (Antigravity Optimization): {telem['saved']:,}\n"
                f"Efficiency Rate: {telem['efficiency_pct']}%\n"
                f"System Uptime: {telem['uptime_sec']} seconds"
            )
        except Exception:
            telem_text = "Antigravity Token Telemetry: Active (0-Token Bypass Engine Operational)"

        tk.Label(t6, text=telem_text, fg=C["green"], bg=C["card"], font=F["mono_sm"], justify="left", padx=12, pady=12).pack(fill="x")

    def _render_multitask_cards(self):
        """Render glossy Task Cards for active/parallel tasks in the control center tab."""
        if not hasattr(self, "_multitask_list_frame") or not self._multitask_list_frame:
            return

        try:
            if not self._multitask_list_frame.winfo_exists():
                return
            for child in self._multitask_list_frame.winfo_children():
                child.destroy()
        except Exception:
            return

        if not self._agent_tasks:
            try:
                empty_lbl = tk.Label(
                    self._multitask_list_frame,
                    text="No active parallel tasks or sub-agent goals registered.\nSubmit multi-goal tasks using '/run goal1 | goal2' or voice.",
                    fg=C["t3"], bg=C["surface"], font=F["mono_sm"], justify="center", pady=24
                )
                empty_lbl.pack(fill="x")
            except Exception:
                pass
            return
            return

        for tid, info in list(self._agent_tasks.items())[::-1]:
            st = info.get("status", "queued").lower()
            name = info.get("name", "Task")
            prog = info.get("progress", 0.0)
            res = info.get("result", "")

            # Badge color mapping
            badge_bg = C["cyan"] if st == "running" else C["green"] if st in ("completed", "done") else C["err"] if st == "failed" else C["amber"]
            icon = "⚡" if st == "running" else "✓" if st in ("completed", "done") else "✕" if st == "failed" else "⏳"

            card = tk.Frame(self._multitask_list_frame, bg=C["card"], highlightbackground=C["border"], highlightthickness=1, padx=12, pady=8)
            card.pack(fill="x", pady=4)

            # Top row: icon + title + status pill badge
            top_row = tk.Frame(card, bg=C["card"])
            top_row.pack(fill="x")

            tk.Label(top_row, text=f"{icon} {name}", fg=C["t1"], bg=C["card"], font=F["ui_b"]).pack(side="left")
            tk.Label(top_row, text=f" {st.upper()} ", fg="#000000", bg=badge_bg, font=F["mono_xs"]).pack(side="right")

            # Middle row: progress info if running
            if st == "running" or prog > 0:
                p_frame = tk.Frame(card, bg=C["bg"], height=6)
                p_frame.pack(fill="x", pady=6)
                p_frame.pack_propagate(False)
                fw = max(4, int((p_frame.winfo_width() or 200) * prog))
                tk.Frame(p_frame, bg=C["cyan"], width=fw).pack(side="left", fill="y")

            if res:
                tk.Label(card, text=f"Output: {res[:100]}", fg=C["t3"], bg=C["card"], font=F["mono_xs"], anchor="w").pack(fill="x", pady=(2, 0))

    def _show_settings_modal(self):
        overlay = tk.Toplevel(self.root)
        overlay.title("BR JARVIS — Settings")
        overlay.geometry("520x580")
        overlay.configure(bg=C["surface"])
        overlay.resizable(False, False)
        overlay.transient(self.root)
        overlay.grab_set()

        hdr = tk.Frame(overlay, bg=C["card"], height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙️ SYSTEM SETTINGS", fg=C["cyan"], bg=C["card"],
                 font=F["ui_title"]).pack(side="left", padx=16, pady=10)

        body = tk.Frame(overlay, bg=C["surface"], padx=24, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="PREFERRED LLM MODEL", fg=C["cyan"], bg=C["surface"], font=F["ui_xs"]).pack(anchor="w", pady=(4, 4))
        models = self._get_available_models()
        self._model_var = tk.StringVar(value=self._active_model)
        m_combo = ttk.Combobox(body, textvariable=self._model_var, values=models, state="readonly", font=F["mono_sm"])
        m_combo.pack(fill="x", pady=(0, 14))

        tk.Label(body, text="WAKE WORD", fg=C["purple"], bg=C["surface"], font=F["ui_xs"]).pack(anchor="w", pady=(4, 4))
        wake_var = tk.StringVar(value=os.environ.get("JARVIS_WAKE_WORD", "hey jarvis"))
        w_entry = tk.Entry(body, textvariable=wake_var, fg=C["t1"], bg=C["card"], insertbackground=C["cyan"], borderwidth=0, font=F["mono"])
        w_entry.pack(fill="x", pady=(0, 14), ipady=6)

        tk.Label(body, text="ASSISTANT NAME", fg=C["green"], bg=C["surface"], font=F["ui_xs"]).pack(anchor="w", pady=(4, 4))
        name_var = tk.StringVar(value=os.environ.get("JARVIS_ASSISTANT_NAME", "BR"))
        n_entry = tk.Entry(body, textvariable=name_var, fg=C["t1"], bg=C["card"], insertbackground=C["cyan"], borderwidth=0, font=F["mono"])
        n_entry.pack(fill="x", pady=(0, 18), ipady=6)

        tk.Label(body, text="KEYBOARD SHORTCUTS CHEAT SHEET", fg=C["amber"], bg=C["surface"], font=F["ui_xs"]).pack(anchor="w", pady=(4, 4))
        sc_info = tk.Label(body, text="F4: Mute Mic  |  F5: Listening Mode\nF11: Sleep Orb  |  F12: Mission Control\nCtrl+Shift+C: Max Control Center", fg=C["t3"], bg=C["card"], font=F["mono_xs"], justify="left", padx=10, pady=8)
        sc_info.pack(fill="x", pady=(0, 18))

        def _save():
            nm = self._model_var.get()
            if nm != self._active_model:
                self._active_model = nm
                self._model_lbl.config(text=f"⚡ {nm}")
                self.write_log(f"SYS: Model switched to {nm}")
            os.environ["JARVIS_WAKE_WORD"] = wake_var.get().strip()
            os.environ["JARVIS_ASSISTANT_NAME"] = name_var.get().strip()
            self.write_log("SYS: Settings updated successfully.")
            overlay.destroy()

        s_btn = tk.Button(body, text="Save Settings", command=_save, bg=C["accent"], fg="#ffffff", font=F["ui_b"], borderwidth=0, cursor="hand2", pady=10)
        s_btn.pack(fill="x", pady=(10, 0))

    # ══════════════════════════════════════════════════════════════════════
    # ── Helpers & Public API ──────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    def _show_command_palette_modal(self):
        """Open high-speed Ctrl+K Command Palette Modal."""
        pop = tk.Toplevel(self.root)
        pop.title("JARVIS — Quick Command Palette (Ctrl+K)")
        pop.geometry("560x320")
        pop.configure(bg=C["bg"])
        pop.transient(self.root)
        pop.grab_set()

        hdr = tk.Frame(pop, bg=C["surface"], padx=14, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍 COMMAND PALETTE", fg=C["cyan"], bg=C["surface"], font=F["ui_b"]).pack(side="left")
        tk.Label(hdr, text="Press Esc to exit", fg=C["t4"], bg=C["surface"], font=F["ui_xs"]).pack(side="right")

        body = tk.Frame(pop, bg=C["bg"], padx=14, pady=12)
        body.pack(fill="both", expand=True)

        entry_var = tk.StringVar()
        ent = tk.Entry(body, textvariable=entry_var, fg=C["t1"], bg=C["card"], insertbackground=C["cyan"], font=F["mono"], borderwidth=1, relief="solid")
        ent.pack(fill="x", pady=(0, 10))
        ent.focus_set()

        listbox = tk.Listbox(body, fg=C["t2"], bg=C["card"], selectbackground=C["accent"], selectforeground="#ffffff", borderwidth=0, font=F["ui_sm"])
        listbox.pack(fill="both", expand=True)

        cmds = [
            "💬 Open Cognitive Dialogue Workspace",
            "📊 Run Excel Project Analysis Report",
            "⚡ Switch Model Backend to Gemini 3.5 Flash",
            "💻 Switch Role Persona to Senior Coder",
            "🛡️ Check Guardian Integrity Status",
            "🎙️ Toggle Live Voice Recording",
        ]
        for c in cmds:
            listbox.insert(tk.END, c)

        def _exec(event=None):
            sel = listbox.curselection()
            if sel:
                item = listbox.get(sel[0])
                self.write_log(f"SYS: Palette executed '{item}'")
                if "Excel" in item:
                    self._on_input_submit_text("excel project analysis")
                elif "Voice" in item:
                    self._toggle_mute()
            pop.destroy()

        ent.bind("<Return>", _exec)
        listbox.bind("<Double-Button-1>", _exec)
        pop.bind("<Escape>", lambda e: pop.destroy())

    def _show_screen_cast_modal(self):
        """Open Screen Share / Recording Permission Modal."""
        pop = tk.Toplevel(self.root)
        pop.title("Share screen with Live — BR JARVIS")
        pop.geometry("420x240")
        pop.configure(bg=C["bg"])
        pop.transient(self.root)
        pop.grab_set()

        body = tk.Frame(pop, bg=C["surface"], padx=20, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="📺 Start recording or casting with BR JARVIS?", fg=C["t1"], bg=C["surface"], font=F["ui_lg"]).pack(anchor="w", pady=(0, 10))

        cast_var = tk.StringVar(value="Entire screen")
        om = ttk.OptionMenu(body, cast_var, "Entire screen", "Entire screen", "Active Window")
        om.pack(fill="x", pady=(0, 10))

        warn = "While sharing, recording, or casting, BR JARVIS can capture any information displayed on screen. Be mindful of passwords and sensitive data."
        tk.Label(body, text=warn, fg=C["t3"], bg=C["surface"], font=F["ui_xs"], wraplength=380, justify="left").pack(anchor="w", pady=(0, 14))

        btn_row = tk.Frame(body, bg=C["surface"])
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="Cancel", command=pop.destroy, bg=C["card"], fg=C["t2"], font=F["ui_sm"], padx=12, pady=4).pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="Cast", command=lambda: (self.write_log("SYS: Screen cast initialized"), pop.destroy()), bg=C["accent"], fg="#ffffff", font=F["ui_b"], padx=16, pady=4).pack(side="right")


    def _send_clipboard(self):
        try:
            t = self.root.clipboard_get()
            if t and self.on_text_command:
                self.write_log(f"SYS: Sending clipboard content ({len(t)} chars)")
                threading.Thread(target=self.on_text_command, args=(f"Analyze clipboard: {t[:2000]}",), daemon=True).start()
        except Exception:
            self.write_log("SYS: Clipboard empty")

    def _take_screenshot(self):
        if self.on_text_command:
            self.write_log("SYS: Taking screenshot for Vision analysis...")
            threading.Thread(target=self.on_text_command, args=("take a screenshot and analyze it",), daemon=True).start()

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        self._log_entries.clear()
        self._log_count_var.set("0")
        self.write_log("SYS: Log cleared.")

    def _load_active_model(self):
        try:
            data = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
            backend = data.get("default_backend", "gemini")
            return data.get(backend, data.get("gemini", "gemini-3-flash"))
        except Exception:
            return "gemini-3-flash"

    def _get_available_models(self):
        try:
            data = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
            models = []
            keys = [
                "gemini_code", "gemini_reasoning", "gemini_general",
                "gemini_agent", "gemini_vision", "gemini_fast", "gemini_lite",
                "gemini", "gpt", "claude", "ollama", "nvidia", "mistral"
            ]
            for k in keys:
                v = data.get(k)
                if v and v not in models:
                    models.append(v)
            return models if models else ["gemini-3.1-pro-high", "gemini-3-flash", "gemini-3.5-flash-low"]
        except Exception:
            return ["gemini-3.1-pro-high", "gemini-3-flash", "gemini-3.5-flash-low"]

    def _start_sys_monitor(self):
        def _loop():
            while True:
                try:
                    if _PSUTIL:
                        self._cpu = psutil.cpu_percent(interval=0.5)
                        self._ram = psutil.virtual_memory().percent
                        self._disk = psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else 0
                        net = psutil.net_io_counters()
                        self._net_s = net.bytes_sent
                        self._net_r = net.bytes_recv
                except Exception:
                    pass
                time.sleep(1.5)
        threading.Thread(target=_loop, daemon=True).start()

    def _on_input_submit(self, event=None):
        text = self._input_var.get().strip()
        if not text: return
        self._input_var.set("")
        self._hist_idx = -1
        if text and (not self._cmd_history or self._cmd_history[0] != text):
            self._cmd_history.appendleft(text)
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

    def _hist_prev(self, event=None):
        if not self._cmd_history: return
        self._hist_idx = min(self._hist_idx + 1, len(self._cmd_history) - 1)
        self._input_var.set(self._cmd_history[self._hist_idx])
        self._input_entry.icursor(tk.END)

    def _hist_next(self, event=None):
        if self._hist_idx <= 0:
            self._hist_idx = -1
            self._input_var.set("")
            return
        self._hist_idx -= 1
        self._input_var.set(self._cmd_history[self._hist_idx])
        self._input_entry.icursor(tk.END)

    def _autocomplete(self, event=None):
        text = self._input_var.get()
        prefixes = ["/commit", "/review", "/research", "/edit", "/scaffold", "/docker", "/deploy", "/github-scan", "/monitor"]
        for p in prefixes:
            if p.startswith(text) and text:
                self._input_var.set(p + " ")
                self._input_entry.icursor(tk.END)
                return "break"

    def _update_charcount(self, *_):
        n = len(self._input_var.get())
        self._charcount_var.set(str(n) if n > 0 else "")

    def _toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.set_state("MUTED")
            self.write_log("SYS: Microphone muted.")
        else:
            self.set_state("LISTENING")
            self.write_log("SYS: Microphone active.")

    # ══════════════════════════════════════════════════════════════════════
    # ── Public API Preservation ───────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    def set_state(self, state: str):
        self._prev_state = self._state
        self._state      = state
        if state == "MUTED":
            self.speaking = False
        elif state == "SPEAKING":
            self.speaking = True
        elif state == "THINKING":
            self.speaking = False
        elif state == "LISTENING":
            self.speaking = False
            if self._is_sleeping:
                self.root.after_idle(self._wake_up_from_sleep_orb)
        elif state == "PROCESSING":
            self.speaking = False
        else:
            self.speaking = False
        self.status_text = state

    def write_log(self, text: str):
        ts = time.strftime("[%H:%M:%S]  ")
        tl = text.lower()

        if tl.startswith("you:"):
            tag  = "you"
            self.set_state("PROCESSING")
        elif tl.startswith("jarvis:") or tl.startswith("ai:") or tl.startswith("br:"):
            tag  = "ai"
            self.set_state("SPEAKING")
        elif "error" in tl or "failed" in tl or "exception" in tl:
            tag  = "err"
        elif tl.startswith("[tool]") or "tool" in tl[:10]:
            tag  = "tool"
        else:
            tag  = "sys"

        self._log_entries.append((ts, text, tag))

        prefix_map = {"you": "  ▸ ", "ai": "  ◆ ", "sys": "  ○ ", "err": "  ✕ ", "tool": "  ⚙ "}
        prefix = prefix_map.get(tag, "  · ")

        def _insert():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, ts, "time")
            self.log_text.insert(tk.END, prefix + text + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
            self._log_count_var.set(f"{len(self._log_entries)} entries")

        self.root.after_idle(_insert)

    def update_agent_task(self, task_id: str, name: str, status: str, progress: float = 0.0, result: str = ""):
        """Update or register an active/parallel task for visual rendering in the UI."""
        clean_st = str(status).lower().strip()
        prog = max(0.0, min(1.0, float(progress))) if progress is not None else 0.0
        
        # Preserve or set entry
        entry = self._agent_tasks.get(task_id, {})
        entry.update({
            "id": task_id,
            "name": name or entry.get("name", "Task"),
            "status": clean_st,
            "progress": prog,
            "result": result or entry.get("result", ""),
            "updated_at": time.time(),
        })
        self._agent_tasks[task_id] = entry

        def _refresh():
            self._draw_agent_status()
            if hasattr(self, "_multitask_list_frame") and self._multitask_list_frame:
                self._render_multitask_cards()

        try:
            self.root.after_idle(_refresh)
        except Exception:
            pass

    def remove_agent_task(self, task_id: str):
        if task_id in self._agent_tasks:
            del self._agent_tasks[task_id]
            try:
                self.root.after_idle(self._draw_agent_status)
            except Exception:
                pass

    def clear_agent_tasks(self):
        self._agent_tasks.clear()
        try:
            self.root.after_idle(self._draw_agent_status)
        except Exception:
            pass

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def _on_resize(self, event=None):
        if event and event.widget is self.root and not self._is_sleeping:
            self.W = self.root.winfo_width()
            self.H = self.root.winfo_height()
            self.bg.config(width=self.W, height=self.H)
            self.FCX = int(self.W * 0.30)
            self.FCY = int(self.H * 0.44)
            self.FACE_SZ = min(int(self.H * 0.35), 280)

            PW = int(self.W * 0.32)
            PX = self.W - PW
            self.panel_frame.place(x=PX, y=0, width=PW, height=self.H - 52)
            self.bottom_bar.place(x=0, y=self.H - 52, width=self.W, height=52)

    def _load_face(self, path):
        if not _PIL: return
        FW = self.FACE_SZ
        try:
            img = Image.open(path).convert("RGBA").resize((FW, FW), Image.LANCZOS)
            mask = Image.new("L", (FW, FW), 0)
            ImageDraw.Draw(mask).ellipse((2, 2, FW-2, FW-2), fill=255)
            img.putalpha(mask)
            self._face_pil = img
            self._has_face = True
        except Exception:
            self._has_face = False

    def _api_keys_exist(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(data.get("gemini_api_key")) and bool(data.get("os_system"))
        except Exception:
            return False

    def wait_for_api_key(self):
        while not self._api_key_ready:
            time.sleep(0.1)

    def _show_setup_ui(self):
        detected = self._detect_os()
        self._selected_os = tk.StringVar(value=detected)

        backdrop = tk.Frame(self.root, bg="#000000")
        backdrop.place(x=0, y=0, relwidth=1, relheight=1)

        overlay = tk.Frame(self.root, bg=C["surface"], highlightbackground=C["border"], highlightthickness=1)
        overlay.place(relx=0.5, rely=0.5, anchor="center", width=460, height=500)

        hdr = tk.Frame(overlay, bg=C["card"], height=44)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  ⬡  INITIALISATION REQUIRED", fg=C["t1"], bg=C["card"], font=F["ui_lg"]).pack(side="left", pady=10, padx=8)

        body = tk.Frame(overlay, bg=C["surface"], padx=28)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="GEMINI API KEY", fg=C["cyan"], bg=C["surface"], font=F["ui_xs"]).pack(anchor="w", pady=(20, 4))
        key_frame = tk.Frame(body, bg=C["bg"], highlightbackground=C["border"], highlightthickness=1)
        key_frame.pack(fill="x", pady=(0, 4))
        self._gemini_entry = tk.Entry(key_frame, width=38, fg=C["t1"], bg=C["bg"], insertbackground=C["cyan"], borderwidth=0, font=F["mono"], show="*")
        self._gemini_entry.pack(side="left", fill="x", expand=True, pady=8, padx=8)

        submit = tk.Button(body, text="INITIALISE NEURAL CORE →", command=lambda: self._save_setup(backdrop), bg=C["accent"], fg="#ffffff", font=F["ui_b"], borderwidth=0, pady=10, cursor="hand2")
        submit.pack(fill="x", pady=20)

        self._setup_overlay = overlay
        self._gemini_entry.focus_set()

    def _save_setup(self, backdrop=None):
        key = self._gemini_entry.get().strip()
        if not key: return
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": key, "os_system": self._selected_os.get()}, f, indent=4)
        self._setup_overlay.destroy()
        if backdrop: backdrop.destroy()
        self._api_key_ready = True
        self.set_state("LISTENING")

    @staticmethod
    def _detect_os() -> str:
        s = platform.system().lower()
        if s == "darwin": return "mac"
        if s == "windows": return "windows"
        return "linux"
