"""
Estate OS — Personal Estate Plan
==================================
Desktop application for recording an estate plan through a guided interview.
A female British voice reads each question aloud. Answers are saved automatically
after every response so the session can be stopped and resumed at any time.

USAGE:
  Double-click launch_estate_interview.bat
  Or: python behaviors/estate-interview/estate_interview.py

REQUIRED:  pip install customtkinter reportlab
VOICE OUT:  pip install edge-tts
VOICE IN:   Windows Speech Recognition (built-in, no packages needed)
"""

import customtkinter as ctk
import json
import os
import sys
import threading
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox
import tkinter as tk

# ── Optional voice dependencies ────────────────────────────────────────────────

import subprocess as _subp
import platform

TTS_AVAILABLE = False
SR_AVAILABLE  = platform.system() == "Windows"   # Windows Speech Recognition built-in

try:
    import edge_tts
    import asyncio
    TTS_AVAILABLE = True
except Exception:
    pass

_voice_process = None   # current recording subprocess

# ── Local modules ──────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent))
from questions import CHAPTERS
from pdf_generator import generate_pdf

# ── Constants ──────────────────────────────────────────────────────────────────

APP_DIR      = Path(__file__).parent
PROFILES_DIR = APP_DIR / "profiles"

# Light theme — warm off-white, ChatGPT-style
BG         = "#F9F7F4"   # warm off-white main background
PANEL      = "#F0EDE8"   # slightly deeper sidebar / bars
CARD       = "#FFFFFF"   # pure white cards
GOLD       = "#B8860B"   # darker gold (readable on white)
GOLD_HOVER = "#8B6508"
TEXT       = "#1A1A1A"   # near-black body text
TEXT_DIM   = "#6B6868"   # medium grey labels
GREEN      = "#1A7F37"
GREEN_LT   = "#2DA44E"
BORDER     = "#E0DDD6"   # warm light border
INPUT_BG   = "#F5F3EF"   # slightly off-white input fields
RED        = "#C0392B"
RED_DIM    = "#922B21"
AMBER      = "#B7770D"

ctk.set_appearance_mode("light")

FONT_BODY    = ("Segoe UI", 13)
FONT_LABEL   = ("Segoe UI", 12)
FONT_LARGE   = ("Segoe UI", 20, "bold")
FONT_TINY    = ("Segoe UI", 11)

# Essential chapter IDs shown when user picks "Essential only"
ESSENTIAL_CHAPTERS = {
    "about_you", "your_family", "key_people",
    "your_documents", "finances", "property",
    "digital_life", "your_wishes", "messages",
}

# Chapter group labels for the selection screen
CHAPTER_GROUPS = [
    ("Part One — Your Estate Plan",                   list(range(9))),
    ("Part One Extended — Complex Estates & Operations", list(range(9, 13))),
    ("Part Two — Your History",                       list(range(13, 15))),
]


# ── Voice output ───────────────────────────────────────────────────────────────

_tts_stop    = threading.Event()
_tts_process = None


def speak(text: str) -> None:
    """Speak text using edge-tts British female voice. Non-blocking."""
    if not TTS_AVAILABLE:
        return
    stop_speaking()
    _tts_stop.clear()

    def _run():
        global _tts_process
        tmp_path = None
        try:
            async def _save():
                communicate = edge_tts.Communicate(text, "en-GB-SoniaNeural")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                    p = f.name
                await communicate.save(p)
                return p

            tmp_path = asyncio.run(_save())
            if _tts_stop.is_set():
                return
            ps = (
                "Add-Type -AssemblyName presentationCore; "
                f"$mp = New-Object System.Windows.Media.MediaPlayer; "
                f"$mp.Open([uri]'{tmp_path}'); "
                "$mp.Play(); Start-Sleep 60"
            )
            _tts_process = _subp.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=_subp.CREATE_NO_WINDOW,
                stdout=_subp.DEVNULL, stderr=_subp.DEVNULL,
            )
            _tts_process.wait()
        except Exception:
            pass
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    threading.Thread(target=_run, daemon=True).start()


def stop_speaking() -> None:
    global _tts_process
    _tts_stop.set()
    if _tts_process:
        try:
            _tts_process.kill()
        except Exception:
            pass
        _tts_process = None


# ── Profile ────────────────────────────────────────────────────────────────────

class Profile:
    def __init__(self, name: str):
        self.name = name
        safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
        self.filepath          = PROFILES_DIR / f"{safe.replace(' ', '_')}.json"
        self.answers:          dict = {}
        self.current_chapter:  int  = 0
        self.current_question: int  = 0
        self.enabled_chapters: list = []   # empty list = all chapters enabled
        self.created      = datetime.now().strftime("%B %d, %Y")
        self.last_updated = self.created
        if self.filepath.exists():
            self._load()

    def _load(self):
        try:
            data = json.loads(self.filepath.read_text(encoding="utf-8"))
            self.answers           = data.get("answers", {})
            self.current_chapter   = data.get("current_chapter", 0)
            self.current_question  = data.get("current_question", 0)
            self.enabled_chapters  = data.get("enabled_chapters", [])
            self.created           = data.get("created", self.created)
            self.last_updated      = data.get("last_updated", self.created)
        except Exception:
            pass

    def save(self):
        self.last_updated = datetime.now().strftime("%B %d, %Y")
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(json.dumps({
            "name":             self.name,
            "created":          self.created,
            "last_updated":     self.last_updated,
            "answers":          self.answers,
            "current_chapter":  self.current_chapter,
            "current_question": self.current_question,
            "enabled_chapters": self.enabled_chapters,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_answer(self, q_id: str, value: str):
        self.answers[q_id] = value
        self.save()

    def get_answer(self, q_id: str) -> str:
        return self.answers.get(q_id, "")

    def is_chapter_enabled(self, ch_id: str) -> bool:
        if not self.enabled_chapters:
            return True
        return ch_id in self.enabled_chapters

    def enabled_indices(self) -> list:
        return [i for i, ch in enumerate(CHAPTERS) if self.is_chapter_enabled(ch["id"])]

    def next_enabled_chapter(self, from_idx: int):
        for i in self.enabled_indices():
            if i > from_idx:
                return i
        return None

    def total_q(self) -> int:
        if not self.enabled_chapters:
            return sum(len(ch["questions"]) for ch in CHAPTERS)
        return sum(len(ch["questions"]) for ch in CHAPTERS
                   if ch["id"] in self.enabled_chapters)

    def answered_count(self) -> int:
        enabled_ids = (set(self.enabled_chapters) if self.enabled_chapters
                       else {q["id"] for ch in CHAPTERS for q in ch["questions"]})
        return sum(1 for qid, v in self.answers.items()
                   if qid in enabled_ids and str(v).strip())

    def pct(self) -> int:
        t = self.total_q()
        return int(self.answered_count() / t * 100) if t else 0

    def chapter_counts(self, idx: int) -> tuple:
        ch = CHAPTERS[idx]
        total    = len(ch["questions"])
        answered = sum(1 for q in ch["questions"]
                       if self.answers.get(q["id"], "").strip())
        return answered, total

    def chapter_done(self, idx: int) -> bool:
        a, t = self.chapter_counts(idx)
        return t > 0 and a == t

    def chapter_started(self, idx: int) -> bool:
        return any(self.answers.get(q["id"], "").strip()
                   for q in CHAPTERS[idx]["questions"])


# ── ChapterButton widget ───────────────────────────────────────────────────────

class ChapterButton(ctk.CTkFrame):
    def __init__(self, parent, chapter, idx, active, done, started, a, t, enabled,
                 on_click, on_toggle, **kw):
        super().__init__(parent, fg_color="transparent", **kw)

        # Row background
        bg = CARD if active else "transparent"
        self.configure(fg_color=bg, corner_radius=6,
                       border_color=GOLD if active else "transparent", border_width=1 if active else 0)
        self.grid_columnconfigure(1, weight=1)

        # Status indicator (left column)
        if not enabled:
            st_text, st_color = "—", BORDER
            st_font = ("Segoe UI", 11)
        elif done:
            st_text, st_color = "✓", GREEN_LT
            st_font = ("Segoe UI Bold", 15)
        elif started:
            st_text, st_color = "◑", GOLD
            st_font = ("Segoe UI", 13)
        else:
            st_text, st_color = "○", TEXT_DIM
            st_font = ("Segoe UI", 11)

        status = ctk.CTkLabel(self, text=st_text, font=st_font,
                              text_color=st_color, width=24)
        status.grid(row=0, column=0, rowspan=2, padx=(10, 4), pady=(8, 8), sticky="n")

        # Chapter title
        nc = TEXT if (enabled and (active or done or started)) else (TEXT_DIM if enabled else BORDER)
        title_lbl = ctk.CTkLabel(self, text=chapter["title"],
                                  font=("Segoe UI Semibold", 11), text_color=nc,
                                  anchor="w", wraplength=170, justify="left")
        title_lbl.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(8, 0))

        # Progress sub-label
        if enabled:
            sub = f"{a} of {t} answered" if a > 0 else f"{t} questions"
        else:
            sub = "not included"
        sub_lbl = ctk.CTkLabel(self, text=sub,
                               font=("Segoe UI", 9),
                               text_color=TEXT_DIM if enabled else BORDER, anchor="w")
        sub_lbl.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=(0, 4))

        # Include / Skip toggle (right column, full height)
        if enabled:
            tog_text = "Skip"
            tog_fg   = "transparent"
            tog_tc   = TEXT_DIM
            tog_bc   = BORDER
        else:
            tog_text = "Include"
            tog_fg   = "transparent"
            tog_tc   = GOLD
            tog_bc   = GOLD

        tog = ctk.CTkButton(self, text=tog_text, width=64, height=28,
                            font=("Segoe UI", 9), corner_radius=14,
                            fg_color=tog_fg, hover_color=PANEL,
                            text_color=tog_tc, border_color=tog_bc, border_width=1,
                            command=lambda: on_toggle(chapter["id"]))
        tog.grid(row=0, column=2, rowspan=2, padx=(4, 10), pady=8)

        # Hover + click bindings (only on enabled chapters, but toggle always works)
        if enabled:
            for w in (self, status, title_lbl, sub_lbl):
                w.bind("<Button-1>", lambda e: on_click(idx))
            self.bind("<Enter>", lambda e: self.configure(fg_color=CARD))
            self.bind("<Leave>",
                      lambda e: self.configure(fg_color=CARD if active else "transparent"))


# ── Main application ───────────────────────────────────────────────────────────

class EstateInterviewApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Estate OS — Personal Estate Plan")
        self.geometry("1320x840")
        self.minsize(1100, 720)
        self.configure(fg_color=BG)

        self.profile:            Profile | None = None
        self.muted:              bool  = False
        self._recording:         bool  = False
        self._chapter_buttons:   list  = []
        self._answer_widget            = None
        self._input_mode:        str   = "text"
        self._sel_minutes:       int   = 10
        self._time_btns:         dict  = {}
        self._mode_cards:        dict  = {}
        self._session_end_time         = None
        self._session_total_secs: float = 0
        self._timer_id                 = None
        self._chapter_grid_parent      = None

        self._show_start()

    # ── Utility ────────────────────────────────────────────────────────────────

    def _clear(self):
        stop_speaking()
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        for w in self.winfo_children():
            w.destroy()
        for col in range(4):
            self.grid_columnconfigure(col, weight=0)
        self.grid_rowconfigure(0, weight=0)

    def _card(self, parent, **kw) -> ctk.CTkFrame:
        d = dict(fg_color=CARD, corner_radius=12, border_color=BORDER, border_width=1)
        d.update(kw)
        return ctk.CTkFrame(parent, **d)

    # ─────────────────────────────────────────────────────────────────────────
    # SCREEN 1 — Welcome / Profile Select
    # ─────────────────────────────────────────────────────────────────────────

    def _show_start(self):
        stop_speaking()
        self._clear()
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        profiles = self._list_profiles()
        if profiles:
            self._build_profile_select(profiles)
        else:
            self._build_welcome()

    def _list_profiles(self) -> list:
        out = []
        for f in sorted(PROFILES_DIR.glob("*.json"),
                        key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d    = json.loads(f.read_text(encoding="utf-8"))
                total = sum(len(ch["questions"]) for ch in CHAPTERS)
                ans   = sum(1 for v in d.get("answers", {}).values() if str(v).strip())
                out.append({
                    "name":    d["name"],
                    "updated": d.get("last_updated", ""),
                    "pct":     int(ans / total * 100) if total else 0,
                })
            except Exception:
                pass
        return out

    def _build_welcome(self):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(expand=True, fill="both")
        outer.grid_columnconfigure(0, weight=0, minsize=400)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        # ── Left branding panel ────────────────────────────────────────────────
        left = ctk.CTkFrame(outer, fg_color=PANEL, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")

        mid = ctk.CTkFrame(left, fg_color="transparent")
        mid.place(relx=0.0, rely=0.5, anchor="w", x=52)

        ctk.CTkLabel(mid, text="Estate OS",
                     font=("Segoe UI Light", 16), text_color=GOLD,
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(mid, text="Personal\nEstate Plan",
                     font=("Segoe UI Bold", 40), text_color=TEXT,
                     anchor="w", justify="left").pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(mid,
                     text="A private, secure record\nfor your family.\nEven five minutes matters.",
                     font=("Segoe UI", 14), text_color=TEXT_DIM,
                     anchor="w", justify="left").pack(anchor="w", pady=(22, 0))

        priv = ctk.CTkFrame(left, fg_color="transparent")
        priv.place(relx=0.0, rely=1.0, anchor="sw", x=52, y=-40)
        ctk.CTkLabel(priv,
                     text="Private  ·  Local  ·  No account needed",
                     font=("Segoe UI", 11), text_color=TEXT_DIM, anchor="w").pack(anchor="w")

        # ── Right panel ───────────────────────────────────────────────────────
        right = ctk.CTkFrame(outer, fg_color=CARD, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")

        scroll = ctk.CTkScrollableFrame(right, fg_color="transparent",
                                         scrollbar_button_color=BORDER)
        scroll.pack(fill="both", expand=True, padx=0, pady=0)
        scroll.grid_columnconfigure(0, weight=1)

        # What is Estate OS?
        ctk.CTkLabel(scroll, text="What is Estate OS?",
                     font=("Segoe UI Bold", 26), text_color=TEXT,
                     anchor="w").pack(anchor="w", padx=52, pady=(44, 12))

        bullets = [
            ("📋", "Guided interview",
             "Answer questions at your own pace — by voice or by typing. "
             "Each session can be as short as five minutes."),
            ("👨‍👩‍👧", "Everything your family needs",
             "Covers your estate plan, finances, property, vehicles, home operations, "
             "digital accounts, media systems, and your personal history."),
            ("🔒", "Completely private",
             "Nothing leaves this computer. No cloud, no account, no internet required. "
             "Your answers are saved locally as you go."),
            ("📄", "Export a finished document",
             "When you're done, generate a PDF estate plan you can print, store in your "
             "safe, and share with your executor."),
        ]
        for icon, title, desc in bullets:
            row = ctk.CTkFrame(scroll, fg_color=BG, corner_radius=10)
            row.pack(fill="x", padx=52, pady=5)
            ctk.CTkLabel(row, text=icon, font=("Segoe UI", 22)).pack(side="left", padx=(18, 0), pady=16)
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, padx=16, pady=14)
            ctk.CTkLabel(txt, text=title, font=("Segoe UI Semibold", 13),
                         text_color=TEXT, anchor="w").pack(anchor="w")
            ctk.CTkLabel(txt, text=desc, font=("Segoe UI", 12),
                         text_color=TEXT_DIM, anchor="w", wraplength=480,
                         justify="left").pack(anchor="w")

        # Divider
        ctk.CTkFrame(scroll, fg_color=BORDER, height=1).pack(fill="x", padx=52, pady=(24, 20))

        ctk.CTkLabel(scroll, text="Let's begin.",
                     font=("Segoe UI Bold", 22), text_color=TEXT,
                     anchor="w").pack(anchor="w", padx=52, pady=(0, 4))
        ctk.CTkLabel(scroll,
                     text="Enter your name to create your estate plan.",
                     font=("Segoe UI", 14), text_color=TEXT_DIM,
                     anchor="w").pack(anchor="w", padx=52, pady=(0, 16))

        ctk.CTkLabel(scroll, text="Your full name",
                     font=("Segoe UI", 12), text_color=TEXT_DIM, anchor="w").pack(anchor="w", padx=52)
        name_entry = ctk.CTkEntry(scroll, width=400, height=50,
                                   font=("Segoe UI", 14),
                                   placeholder_text="e.g. John Robert Haefele",
                                   fg_color=INPUT_BG, border_color=BORDER, text_color=TEXT)
        name_entry.pack(anchor="w", padx=52, pady=(6, 20))
        name_entry.bind("<Return>", lambda e: self._start_new(name_entry.get()))

        ctk.CTkButton(scroll, text="Begin My Estate Plan  →",
                      font=("Segoe UI Semibold", 15), height=52, width=400,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      command=lambda: self._start_new(name_entry.get())).pack(anchor="w", padx=52, pady=(0, 48))
        name_entry.focus()

    def _build_profile_select(self, profiles: list):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(expand=True, fill="both")
        outer.grid_columnconfigure(0, weight=0, minsize=400)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        # ── Left branding panel ────────────────────────────────────────────────
        left = ctk.CTkFrame(outer, fg_color=PANEL, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")

        mid = ctk.CTkFrame(left, fg_color="transparent")
        mid.place(relx=0.0, rely=0.5, anchor="w", x=52)

        ctk.CTkLabel(mid, text="Estate OS",
                     font=("Segoe UI Light", 16), text_color=GOLD,
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(mid, text="Welcome\nback.",
                     font=("Segoe UI Bold", 40), text_color=TEXT,
                     anchor="w", justify="left").pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(mid,
                     text="Continue where you left off,\nor start a new plan.",
                     font=("Segoe UI", 14), text_color=TEXT_DIM,
                     anchor="w", justify="left").pack(anchor="w", pady=(22, 0))

        priv = ctk.CTkFrame(left, fg_color="transparent")
        priv.place(relx=0.0, rely=1.0, anchor="sw", x=52, y=-40)
        ctk.CTkLabel(priv,
                     text="Private  ·  Local  ·  No account needed",
                     font=("Segoe UI", 11), text_color=TEXT_DIM, anchor="w").pack(anchor="w")

        # ── Right panel — profile list ─────────────────────────────────────────
        right = ctk.CTkFrame(outer, fg_color=CARD, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Sub-header in the right pane
        rhdr = ctk.CTkFrame(right, fg_color="transparent", height=80)
        rhdr.grid(row=0, column=0, sticky="ew", padx=52, pady=(0, 0))
        rhdr.grid_propagate(False)
        ctk.CTkLabel(rhdr, text="Your Plans",
                     font=("Segoe UI Semibold", 22), text_color=TEXT,
                     anchor="w").place(x=0, y=36)

        # Scrollable profile list
        scroll = ctk.CTkScrollableFrame(right, fg_color="transparent",
                                         scrollbar_button_color=BORDER)
        scroll.grid(row=1, column=0, sticky="nsew", padx=36, pady=0)

        for p in profiles:
            row = self._card(scroll, corner_radius=10)
            row.pack(fill="x", pady=5)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", padx=22, pady=16, fill="x", expand=True)
            ctk.CTkLabel(info, text=p["name"],
                         font=("Segoe UI Semibold", 15), text_color=TEXT,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info,
                         text=f"{p['pct']}% complete  ·  Last updated {p['updated']}",
                         font=FONT_TINY, text_color=TEXT_DIM, anchor="w").pack(anchor="w")
            ctk.CTkButton(row, text="Continue →", width=130, height=38,
                          fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                          font=("Segoe UI Semibold", 13),
                          command=lambda n=p["name"]: self._load_profile(n)).pack(
                side="right", padx=22, pady=16)

        # Footer strip in right pane
        rfooter = ctk.CTkFrame(right, fg_color=BG, height=70, corner_radius=0)
        rfooter.grid(row=2, column=0, sticky="ew")
        rfooter.grid_propagate(False)
        ctk.CTkButton(rfooter, text="+ Start a new plan",
                      fg_color="transparent", hover_color=CARD,
                      text_color=GOLD, font=("Segoe UI Semibold", 13), height=40,
                      border_color=GOLD, border_width=1, width=200,
                      command=self._build_welcome).pack(side="left", padx=36, pady=15)

    def _start_new(self, name: str):
        name = name.strip()
        if not name:
            return
        self.profile = Profile(name)
        # Default: all chapters enabled
        self.profile.enabled_chapters = [ch["id"] for ch in CHAPTERS]
        self.profile.save()
        self._show_chapter_selection()

    def _load_profile(self, name: str):
        self.profile = Profile(name)
        self._show_interview()

    # ─────────────────────────────────────────────────────────────────────────
    # SCREEN 2 — Chapter Selection
    # ─────────────────────────────────────────────────────────────────────────

    def _show_chapter_selection(self):
        self._clear()
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(expand=True, fill="both")
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # Header bar
        hdr = ctk.CTkFrame(outer, fg_color=PANEL, height=74, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Estate OS", font=("Segoe UI Light", 11),
                     text_color=GOLD, anchor="w").place(x=36, y=14)
        ctk.CTkLabel(hdr, text="Choose your sections",
                     font=("Segoe UI Semibold", 18), text_color=TEXT,
                     anchor="w").place(x=36, y=36)

        # Sub-header with quick-select buttons
        sub = ctk.CTkFrame(outer, fg_color="transparent")
        sub.grid(row=1, column=0, sticky="ew", padx=36, pady=(18, 6))
        ctk.CTkLabel(sub,
                     text="Toggle each section on or off. You can change this at any time.",
                     font=FONT_BODY, text_color=TEXT_DIM).pack(side="left")
        for label, cmd in [
            ("All",            lambda: self._quick_select("all")),
            ("Essential only", lambda: self._quick_select("essential")),
            ("None",           lambda: self._quick_select("none")),
        ]:
            ctk.CTkButton(sub, text=label, width=100 if label == "Essential only" else 56,
                          height=28, font=FONT_TINY,
                          fg_color="transparent", hover_color=CARD,
                          text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                          command=cmd).pack(side="right", padx=(6, 0))

        # Scrollable grid of chapter cards
        scroll = ctk.CTkScrollableFrame(outer, fg_color="transparent",
                                         scrollbar_button_color=BORDER)
        scroll.grid(row=2, column=0, sticky="nsew", padx=28, pady=0)
        scroll.grid_columnconfigure((0, 1, 2), weight=1)
        outer.grid_rowconfigure(2, weight=1)
        self._chapter_grid_parent = scroll
        self._rebuild_chapter_grid()

        # Footer bar
        footer = ctk.CTkFrame(outer, fg_color=PANEL, height=70, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_propagate(False)
        ctk.CTkButton(footer, text="Continue →",
                      font=("Segoe UI Semibold", 14), height=44, width=200,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      command=self._show_interview).pack(side="right", padx=36, pady=13)
        ctk.CTkButton(footer, text="← Back to Start",
                      font=("Segoe UI", 13), height=38, width=150,
                      fg_color="transparent", hover_color=CARD,
                      text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                      command=self._show_start).pack(side="left", padx=36, pady=16)

    def _rebuild_chapter_grid(self):
        parent = self._chapter_grid_parent
        for w in parent.winfo_children():
            w.destroy()
        row_offset = 0
        for group_label, indices in CHAPTER_GROUPS:
            # Group label row
            sep = ctk.CTkFrame(parent, fg_color="transparent")
            sep.grid(row=row_offset, column=0, columnspan=3,
                     sticky="ew", padx=8, pady=(16, 6))
            ctk.CTkLabel(sep, text=group_label.upper(),
                         font=("Segoe UI Semibold", 9), text_color=TEXT_DIM).pack(side="left")
            ctk.CTkFrame(sep, fg_color=BORDER, height=1).pack(
                side="left", fill="x", expand=True, padx=(10, 0))
            row_offset += 1
            # Chapter cards — 3 per row
            for ri, batch_start in enumerate(range(0, len(indices), 3)):
                batch = indices[batch_start: batch_start + 3]
                for ci, ch_idx in enumerate(batch):
                    ch      = CHAPTERS[ch_idx]
                    enabled = self.profile.is_chapter_enabled(ch["id"])
                    a, t    = self.profile.chapter_counts(ch_idx)
                    self._make_chapter_card(parent, ch, ch_idx, enabled, a, t,
                                            row_offset + ri, ci)
            row_offset += max(1, -(-len(indices) // 3))

    def _make_chapter_card(self, parent, ch, ch_idx, enabled, a, t, row, col):
        bg_c  = CARD if enabled else BG
        bdr_c = GOLD if enabled else BORDER
        frame = ctk.CTkFrame(parent, fg_color=bg_c, corner_radius=10,
                              border_color=bdr_c, border_width=1)
        frame.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 4))
        ctk.CTkLabel(top, text=f"Ch. {ch_idx + 1}",
                     font=("Segoe UI", 9),
                     text_color=GOLD if enabled else BORDER).pack(side="left")

        # Toggle button
        def make_cmd(cid=ch["id"]):
            return lambda: self._toggle_chapter(cid)

        if enabled:
            btn_text, btn_fg, btn_tc, btn_bc = "✓  Included", GREEN, TEXT, GREEN
        else:
            btn_text, btn_fg, btn_tc, btn_bc = "○  Skipped", "transparent", TEXT_DIM, BORDER

        ctk.CTkButton(top, text=btn_text, width=94, height=24,
                      font=("Segoe UI", 9), corner_radius=12,
                      fg_color=btn_fg, hover_color=GREEN,
                      text_color=btn_tc, border_color=btn_bc, border_width=1,
                      command=make_cmd()).pack(side="right")

        ctk.CTkLabel(frame, text=ch["title"],
                     font=("Segoe UI Semibold", 12),
                     text_color=TEXT if enabled else TEXT_DIM,
                     anchor="w", wraplength=230).pack(padx=14, anchor="w")
        ctk.CTkLabel(frame, text=ch.get("subtitle", ""),
                     font=FONT_TINY, text_color=TEXT_DIM,
                     anchor="w").pack(padx=14, anchor="w", pady=(2, 4))
        note = f"{a}/{t} answered" if a > 0 else f"{t} questions"
        ctk.CTkLabel(frame, text=note, font=FONT_TINY,
                     text_color=TEXT_DIM if enabled else BORDER,
                     anchor="w").pack(padx=14, anchor="w", pady=(0, 14))

    def _toggle_chapter(self, ch_id: str):
        if ch_id in self.profile.enabled_chapters:
            self.profile.enabled_chapters.remove(ch_id)
        else:
            self.profile.enabled_chapters.append(ch_id)
        self.profile.save()
        self._rebuild_chapter_grid()

    def _quick_select(self, mode: str):
        if mode == "all":
            self.profile.enabled_chapters = [ch["id"] for ch in CHAPTERS]
        elif mode == "none":
            self.profile.enabled_chapters = []
        elif mode == "essential":
            self.profile.enabled_chapters = [ch["id"] for ch in CHAPTERS
                                              if ch["id"] in ESSENTIAL_CHAPTERS]
        self.profile.save()
        self._rebuild_chapter_grid()

    # ─────────────────────────────────────────────────────────────────────────
    # SCREEN 3 — Session Setup
    # ─────────────────────────────────────────────────────────────────────────

    def _show_session_setup(self):
        self._clear()
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(expand=True, fill="both")
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_rowconfigure(2, weight=0)
        outer.grid_columnconfigure(0, weight=1)

        first = self.profile.name.split()[0]

        # ── Full-bleed header ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(outer, fg_color=PANEL, height=86, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="Estate OS",
                     font=("Segoe UI Light", 11), text_color=GOLD,
                     anchor="w").place(x=52, y=18)
        ctk.CTkLabel(hdr, text=f"Ready when you are, {first}.",
                     font=("Segoe UI Semibold", 24), text_color=TEXT,
                     anchor="w").place(x=52, y=44)

        # ── Content area ──────────────────────────────────────────────────────
        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=52, pady=36)
        content.grid_columnconfigure(0, weight=1)

        # ─ Time section ───────────────────────────────────────────────────────
        ctk.CTkLabel(content, text="HOW LONG DO YOU HAVE?",
                     font=("Segoe UI Semibold", 10), text_color=TEXT_DIM,
                     anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 10))

        time_row = ctk.CTkFrame(content, fg_color="transparent")
        time_row.grid(row=1, column=0, sticky="w", pady=(0, 40))
        self._time_btns   = {}
        self._sel_minutes = 10
        for label, mins in [("5 min", 5), ("10 min", 10), ("15 min", 15),
                             ("20 min", 20), ("30 min", 30), ("No limit", None)]:
            b = ctk.CTkButton(time_row, text=label, height=44, width=100,
                              font=("Segoe UI", 13),
                              fg_color=INPUT_BG, hover_color=CARD,
                              text_color=TEXT, border_color=BORDER, border_width=1,
                              command=lambda m=mins: self._pick_time(m))
            b.pack(side="left", padx=(0, 10))
            self._time_btns[mins] = b
        self._pick_time(10)

        # ─ Mode section ───────────────────────────────────────────────────────
        ctk.CTkLabel(content, text="HOW WOULD YOU LIKE TO ANSWER?",
                     font=("Segoe UI Semibold", 10), text_color=TEXT_DIM,
                     anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 12))

        mode_row = ctk.CTkFrame(content, fg_color="transparent")
        mode_row.grid(row=3, column=0, sticky="w", pady=(0, 0))

        # Voice card
        vc = self._card(mode_row, corner_radius=12, width=280, height=200)
        vc.pack(side="left", padx=(0, 16))
        vc.pack_propagate(False)
        ctk.CTkLabel(vc, text="🎤", font=("Segoe UI", 32)).place(x=24, y=28)
        ctk.CTkLabel(vc, text="Voice Mode",
                     font=("Segoe UI Semibold", 15), text_color=TEXT,
                     anchor="w").place(x=24, y=76)
        ctk.CTkLabel(vc, text="Speak your answers aloud",
                     font=("Segoe UI", 12), text_color=TEXT_DIM,
                     anchor="w").place(x=24, y=104)
        v_lbl   = "Select" if SR_AVAILABLE else "Unavailable"
        v_state = "normal" if SR_AVAILABLE else "disabled"
        self._voice_mode_btn = ctk.CTkButton(vc, text=v_lbl, height=36, width=248,
                                              font=FONT_BODY, state=v_state,
                                              fg_color="transparent", hover_color=CARD,
                                              text_color=TEXT_DIM if SR_AVAILABLE else BORDER,
                                              border_color=BORDER, border_width=1,
                                              command=lambda: self._pick_mode("voice"))
        self._voice_mode_btn.place(x=16, y=148)

        # Text card
        tc = self._card(mode_row, corner_radius=12, width=280, height=200,
                        border_color=GOLD)
        tc.pack(side="left")
        tc.pack_propagate(False)
        ctk.CTkLabel(tc, text="✏️", font=("Segoe UI", 32)).place(x=24, y=28)
        ctk.CTkLabel(tc, text="Text Mode",
                     font=("Segoe UI Semibold", 15), text_color=TEXT,
                     anchor="w").place(x=24, y=76)
        ctk.CTkLabel(tc, text="Type at your own pace",
                     font=("Segoe UI", 12), text_color=TEXT_DIM,
                     anchor="w").place(x=24, y=104)
        self._text_mode_btn = ctk.CTkButton(tc, text="Selected ✓", height=36, width=248,
                                             font=FONT_BODY,
                                             fg_color=GOLD, hover_color=GOLD_HOVER,
                                             text_color="#0D1117",
                                             border_color=GOLD, border_width=1,
                                             command=lambda: self._pick_mode("text"))
        self._text_mode_btn.place(x=16, y=148)
        self._mode_cards = {"voice": vc, "text": tc}
        self._input_mode = "text"

        # ── Footer bar ────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(outer, fg_color=PANEL, height=74, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        ctk.CTkButton(footer, text="Begin Session  →",
                      font=("Segoe UI Semibold", 15), height=46, width=220,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      command=self._begin_session).pack(side="right", padx=52, pady=14)
        ctk.CTkButton(footer, text="← Change sections",
                      font=FONT_BODY, height=38, width=160,
                      fg_color="transparent", hover_color=CARD,
                      text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                      command=self._show_chapter_selection).pack(side="left", padx=52, pady=18)

    def _pick_time(self, mins):
        self._sel_minutes = mins
        for m, btn in self._time_btns.items():
            sel = (m == mins)
            btn.configure(
                fg_color=GOLD if sel else INPUT_BG,
                hover_color=GOLD_HOVER if sel else CARD,
                text_color="#0D1117" if sel else TEXT,
                border_color=GOLD if sel else BORDER,
            )

    def _pick_mode(self, mode: str):
        self._input_mode = mode
        for m, c in self._mode_cards.items():
            c.configure(border_color=GOLD if m == mode else BORDER)
        self._voice_mode_btn.configure(
            fg_color=GOLD if mode == "voice" else "transparent",
            text_color="#0D1117" if mode == "voice" else (TEXT_DIM if SR_AVAILABLE else BORDER),
            text="Selected ✓" if mode == "voice" else "Select",
        )
        self._text_mode_btn.configure(
            fg_color=GOLD if mode == "text" else "transparent",
            text_color="#0D1117" if mode == "text" else TEXT_DIM,
            text="Selected ✓" if mode == "text" else "Select",
        )

    def _begin_session(self):
        if self._sel_minutes is not None:
            self._session_end_time    = datetime.now() + timedelta(minutes=self._sel_minutes)
            self._session_total_secs  = float(self._sel_minutes * 60)
        else:
            self._session_end_time   = None
            self._session_total_secs = 0
        self._show_interview()

    # ─────────────────────────────────────────────────────────────────────────
    # SCREEN 4 — Interview
    # ─────────────────────────────────────────────────────────────────────────

    def _show_interview(self):
        stop_speaking()
        self._clear()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        paned = tk.PanedWindow(self, orient="horizontal",
                               sashwidth=5, sashrelief="flat",
                               bg=BORDER, handlesize=0)
        paned.grid(row=0, column=0, sticky="nsew")

        sb_outer = ctk.CTkFrame(paned, fg_color=PANEL, corner_radius=0, width=310)
        main_outer = ctk.CTkFrame(paned, fg_color=BG, corner_radius=0)
        paned.add(sb_outer, minsize=220, stretch="never")
        paned.add(main_outer, minsize=500, stretch="always")

        self._build_sidebar(sb_outer)
        self._build_main_panel(main_outer)

        enabled = self.profile.enabled_indices()
        ch_idx  = self.profile.current_chapter
        if enabled and ch_idx not in enabled:
            ch_idx = enabled[0]
        self._show_chapter_landing(ch_idx)

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self, sb):
        sb.grid_rowconfigure(2, weight=1)
        sb.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(sb, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        ctk.CTkLabel(hdr, text="Estate OS",
                     font=("Segoe UI Light", 11), text_color=GOLD).pack(anchor="w")
        ctk.CTkLabel(hdr, text=self.profile.name,
                     font=("Segoe UI Semibold", 14), text_color=TEXT).pack(anchor="w")

        # Progress
        pf = ctk.CTkFrame(sb, fg_color="transparent")
        pf.grid(row=1, column=0, sticky="ew", padx=16, pady=(6, 10))
        self._pct_label = ctk.CTkLabel(pf, text=f"{self.profile.pct()}% complete",
                                        font=("Segoe UI", 10), text_color=TEXT_DIM)
        self._pct_label.pack(anchor="w")
        self._progress_bar = ctk.CTkProgressBar(pf, height=5,
                                                  fg_color=BORDER, progress_color=GOLD)
        self._progress_bar.pack(fill="x", pady=(3, 0))
        self._progress_bar.set(self.profile.pct() / 100)

        # Chapter scroll list
        cs = ctk.CTkScrollableFrame(sb, fg_color="transparent",
                                     scrollbar_button_color=BORDER)
        cs.grid(row=2, column=0, sticky="nsew", padx=6, pady=2)
        cs.grid_columnconfigure(0, weight=1)
        self._chapter_scroll = cs
        self._render_chapter_list()

        # Bottom actions
        bot = ctk.CTkFrame(sb, fg_color="transparent")
        bot.grid(row=3, column=0, sticky="ew", padx=12, pady=10)
        ctk.CTkButton(bot, text="✔  Done for Today",
                      height=40, font=("Segoe UI Semibold", 12),
                      fg_color=GREEN, hover_color=GREEN_LT, text_color="#FFFFFF",
                      command=self._finished_for_today).pack(fill="x", pady=(0, 5))
        ctk.CTkButton(bot, text="Export PDF", height=32,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      font=("Segoe UI Semibold", 11),
                      command=self._export_pdf).pack(fill="x", pady=(0, 5))
        ctk.CTkButton(bot, text="Switch Profile", height=28,
                      fg_color="transparent", hover_color=CARD, text_color=TEXT_DIM,
                      font=("Segoe UI", 10), border_color=BORDER, border_width=1,
                      command=self._show_start).pack(fill="x")

    def _render_chapter_list(self):
        for w in self._chapter_scroll.winfo_children():
            w.destroy()
        self._chapter_buttons = []
        for i, ch in enumerate(CHAPTERS):
            a, t    = self.profile.chapter_counts(i)
            enabled = self.profile.is_chapter_enabled(ch["id"])
            btn = ChapterButton(
                self._chapter_scroll, ch, i,
                active   = (i == self.profile.current_chapter),
                done     = self.profile.chapter_done(i),
                started  = self.profile.chapter_started(i),
                a=a, t=t, enabled=enabled,
                on_click  = self._jump_to_chapter,
                on_toggle = self._toggle_chapter_in_sidebar,
            )
            btn.grid(row=i, column=0, sticky="ew", pady=2)
            self._chapter_buttons.append(btn)

    # ── Main panel ─────────────────────────────────────────────────────────────

    def _build_main_panel(self, main):
        self._main = main
        self._main.grid_rowconfigure(1, weight=1)
        self._main.grid_columnconfigure(0, weight=1)

        # ── Top bar
        top = ctk.CTkFrame(self._main, fg_color=PANEL, corner_radius=0, height=54)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(0, weight=1)

        self._chapter_header = ctk.CTkLabel(top, text="",
                                             font=("Segoe UI Semibold", 12),
                                             text_color=TEXT, anchor="w")
        self._chapter_header.grid(row=0, column=0, padx=24, sticky="w")

        ctrl = ctk.CTkFrame(top, fg_color="transparent")
        ctrl.grid(row=0, column=1, padx=12, sticky="e")

        # Timer
        self._timer_label = ctk.CTkLabel(ctrl, text="", width=80,
                                          font=("Segoe UI Semibold", 11), text_color=GOLD)
        self._timer_label.pack(side="left", padx=(0, 8))
        self._timer_bar = ctk.CTkProgressBar(ctrl, height=6, width=90,
                                              fg_color=BORDER, progress_color=GOLD)
        if self._session_end_time:
            self._timer_bar.pack(side="left", padx=(0, 14))
            self._timer_bar.set(1.0)

        # Mode toggle
        self._mode_btn = ctk.CTkButton(
            ctrl,
            text="🎤 Voice" if self._input_mode == "voice" else "✏️  Text",
            width=92, height=30, font=FONT_TINY,
            fg_color="transparent", hover_color=CARD, text_color=TEXT_DIM,
            border_color=BORDER, border_width=1,
            command=self._toggle_mode)
        self._mode_btn.pack(side="left", padx=(0, 8))

        # Mute
        self._mute_btn = ctk.CTkButton(
            ctrl,
            text="🔊 Voice on" if TTS_AVAILABLE else "No voice",
            width=100, height=30, font=FONT_TINY,
            fg_color="transparent", hover_color=CARD,
            text_color=TEXT_DIM if TTS_AVAILABLE else BORDER,
            border_color=BORDER, border_width=1,
            command=self._toggle_mute,
            state="normal" if TTS_AVAILABLE else "disabled")
        self._mute_btn.pack(side="left", padx=(0, 4))

        # ── Scrollable content
        self._content = ctk.CTkScrollableFrame(self._main, fg_color=BG,
                                                scrollbar_button_color=BORDER)
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)

        # ── Nav bar
        nav = ctk.CTkFrame(self._main, fg_color=PANEL, corner_radius=0, height=62)
        nav.grid(row=2, column=0, sticky="ew")
        nav.grid_propagate(False)
        nav.grid_columnconfigure(1, weight=1)

        self._prev_btn = ctk.CTkButton(nav, text="← Previous", width=130, height=38,
                                        fg_color="transparent", hover_color=CARD,
                                        text_color=TEXT_DIM, font=FONT_BODY,
                                        border_color=BORDER, border_width=1,
                                        command=self._go_prev)
        self._prev_btn.grid(row=0, column=0, padx=22, pady=12)

        self._save_label = ctk.CTkLabel(nav, text="", font=FONT_TINY, text_color=TEXT_DIM)
        self._save_label.grid(row=0, column=1)

        self._next_btn = ctk.CTkButton(nav, text="Save & Continue  →",
                                        width=174, height=38,
                                        fg_color=GOLD, hover_color=GOLD_HOVER,
                                        text_color="#0D1117",
                                        font=("Segoe UI Semibold", 12),
                                        command=self._go_next)
        self._next_btn.grid(row=0, column=2, padx=22, pady=12)

        self._skip_btn = ctk.CTkButton(nav, text="Skip →", width=78, height=38,
                                        fg_color="transparent", hover_color=CARD,
                                        text_color=TEXT_DIM, font=FONT_TINY,
                                        border_color="transparent",
                                        command=self._go_skip)
        self._skip_btn.grid(row=0, column=3, padx=(0, 18), pady=12)

    # ── Timer ──────────────────────────────────────────────────────────────────

    def _tick_timer(self):
        if not self._session_end_time:
            return
        remaining = (self._session_end_time - datetime.now()).total_seconds()
        if remaining <= 0:
            self._time_up()
            return
        m, s = int(remaining // 60), int(remaining % 60)
        color = RED if remaining < 60 else (AMBER if remaining < 120 else GOLD)
        self._timer_label.configure(text=f"{m}:{s:02d} left", text_color=color)
        frac = remaining / max(self._session_total_secs, 1)
        self._timer_bar.configure(progress_color=color)
        self._timer_bar.set(max(0.0, min(1.0, frac)))
        self._timer_id = self.after(1000, self._tick_timer)

    def _time_up(self):
        self._save_current_answer()
        self._session_end_time = None
        stop_speaking()
        self._show_time_up_card()

    def _show_time_up_card(self):
        for w in self._content.winfo_children():
            w.destroy()
        card = self._card(self._content, border_color=GOLD, corner_radius=14)
        card.grid(row=0, column=0, sticky="nsew", padx=60, pady=60)
        self._content.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="⏱", font=("Segoe UI", 52)).grid(pady=(44, 8))
        ctk.CTkLabel(card, text="Session complete.",
                     font=("Segoe UI Bold", 24), text_color=TEXT).grid()
        ctk.CTkLabel(card, text="Everything you answered has been saved.",
                     font=("Segoe UI", 13), text_color=TEXT_DIM).grid(pady=(8, 24))
        ctk.CTkLabel(card, text=f"{self.profile.pct()}% of your estate plan is complete.",
                     font=("Segoe UI Semibold", 12), text_color=TEXT).grid()
        pb = ctk.CTkProgressBar(card, height=8, fg_color=BORDER,
                                 progress_color=GOLD, width=360)
        pb.grid(pady=(8, 32))
        pb.set(self.profile.pct() / 100)
        ctk.CTkButton(card, text="Start another session  →",
                      font=("Segoe UI Semibold", 13), height=46, width=260,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      command=self._show_session_setup).grid(pady=(0, 12))
        ctk.CTkButton(card, text="Export PDF",
                      font=FONT_BODY, height=38, width=260,
                      fg_color="transparent", hover_color=CARD, text_color=GOLD,
                      border_color=GOLD, border_width=1,
                      command=self._export_pdf).grid(pady=(0, 40))
        self._chapter_header.configure(text="Session complete")

    def _pause_session(self):
        self._save_current_answer()
        self._session_end_time = None
        self._show_chapter_landing(self.profile.current_chapter)

    def _save_current_answer(self):
        try:
            answer = self._get_current_answer()
            if answer:
                ch = CHAPTERS[self.profile.current_chapter]
                q  = ch["questions"][self.profile.current_question]
                self.profile.set_answer(q["id"], answer)
        except Exception:
            pass

    # ── Input mode toggle ──────────────────────────────────────────────────────

    def _toggle_mode(self):
        self._input_mode = "voice" if self._input_mode == "text" else "text"
        self._mode_btn.configure(
            text="🎤 Voice" if self._input_mode == "voice" else "✏️  Text")
        self._load_question(self.profile.current_chapter,
                            self.profile.current_question, speak_intro=False)

    # ── Question rendering ─────────────────────────────────────────────────────

    def _load_question(self, ch_idx: int, q_idx: int, speak_intro: bool = False):
        ch_idx = max(0, min(ch_idx, len(CHAPTERS) - 1))
        ch     = CHAPTERS[ch_idx]
        q_idx  = max(0, min(q_idx, len(ch["questions"]) - 1))
        self.profile.current_chapter  = ch_idx
        self.profile.current_question = q_idx
        self.profile.save()
        self._recording = False
        self._answer_widget = None

        q    = ch["questions"][q_idx]
        a, t = self.profile.chapter_counts(ch_idx)
        self._chapter_header.configure(
            text=f"{ch['title']}  ·  Question {q_idx + 1} of {t}")

        for w in self._content.winfo_children():
            w.destroy()

        # Chapter intro card (first question only)
        row_offset = 0
        if q_idx == 0:
            ic = self._card(self._content)
            ic.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 12))
            ic.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(ic,
                         text=f"Chapter {ch_idx + 1} of {len(CHAPTERS)}  —  {ch['title']}",
                         font=("Segoe UI", 10), text_color=GOLD,
                         anchor="w").grid(row=0, column=0, padx=20, pady=(16, 2), sticky="w")
            ctk.CTkLabel(ic, text=ch["intro"],
                         font=("Segoe UI", 12), text_color=TEXT_DIM,
                         anchor="w", justify="left", wraplength=620).grid(
                row=1, column=0, padx=20, pady=(0, 16), sticky="w")
            row_offset = 1

        # Question card
        qc = self._card(self._content)
        qc.grid(row=row_offset, column=0, sticky="ew", padx=32,
                pady=(12 if row_offset else 28, 8))
        qc.grid_columnconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Badges
        br = ctk.CTkFrame(qc, fg_color="transparent")
        br.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        if q.get("required"):
            ctk.CTkLabel(br, text="REQUIRED",
                         font=("Segoe UI", 8), text_color=GOLD,
                         fg_color=CARD, corner_radius=4).pack(side="left")
        if q.get("sensitive"):
            ctk.CTkLabel(br, text="  SENSITIVE — this document is private",
                         font=("Segoe UI", 8), text_color=TEXT_DIM).pack(side="left")

        # Question text
        ctk.CTkLabel(qc, text=q["text"],
                     font=FONT_LARGE, text_color=TEXT,
                     anchor="w", justify="left", wraplength=650).grid(
            row=1, column=0, padx=24, pady=(10, 4), sticky="w")

        # Help text
        if q.get("help"):
            ctk.CTkLabel(qc, text=q["help"],
                         font=FONT_TINY, text_color=TEXT_DIM, anchor="w").grid(
                row=2, column=0, padx=24, pady=(0, 8), sticky="w")

        # Input area
        existing = self.profile.get_answer(q["id"])
        if self._input_mode == "voice" and SR_AVAILABLE:
            self._build_voice_area(qc, q, existing, row=3)
        else:
            self._build_text_area(qc, q, existing, row=3)

        # Saved note
        if existing:
            ctk.CTkLabel(qc,
                         text="Currently saved — edit above and click Save & Continue to update.",
                         font=FONT_TINY, text_color=TEXT_DIM).grid(
                row=5, column=0, padx=24, pady=(0, 12), sticky="w")

        is_first = (ch_idx == 0 and q_idx == 0)
        self._prev_btn.configure(state="disabled" if is_first else "normal")
        self._skip_btn.configure(
            state="normal" if not q.get("required") else "disabled",
            text_color=TEXT_DIM if not q.get("required") else BORDER)

        self._render_chapter_list()
        self._update_progress()
        if self._answer_widget:
            try:
                self._answer_widget.focus()
            except Exception:
                pass
        if not self.muted:
            if speak_intro and q_idx == 0:
                speak(ch["intro"] + " " + q["voice"])
            else:
                speak(q["voice"])

    def _build_text_area(self, parent, q, existing, row):
        """Standard text input — single line or multiline."""
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, padx=20, pady=(4, 4), sticky="ew")
        wrap.grid_columnconfigure(0, weight=1)

        if q["type"] == "multiline":
            self._answer_widget = ctk.CTkTextbox(
                wrap, height=130, font=FONT_BODY,
                fg_color=INPUT_BG, border_color=BORDER, border_width=1,
                text_color=TEXT, corner_radius=8)
            self._answer_widget.grid(row=0, column=0, sticky="ew")
            if existing:
                self._answer_widget.insert("1.0", existing)
        else:
            self._answer_widget = ctk.CTkEntry(
                wrap, height=46, font=FONT_BODY,
                placeholder_text=q.get("placeholder", ""),
                fg_color=INPUT_BG, border_color=BORDER, border_width=1,
                text_color=TEXT, corner_radius=8)
            self._answer_widget.grid(row=0, column=0, sticky="ew")
            if existing:
                self._answer_widget.insert(0, existing)
            self._answer_widget.bind("<Return>", lambda e: self._go_next())

        if SR_AVAILABLE:
            ctk.CTkButton(wrap, text="🎤  Switch to voice input",
                          width=176, height=26, font=FONT_TINY,
                          fg_color="transparent", hover_color=CARD, text_color=TEXT_DIM,
                          border_color=BORDER, border_width=1,
                          command=self._switch_to_voice).grid(
                row=1, column=0, sticky="w", pady=(6, 6))

    def _build_voice_area(self, parent, q, existing, row):
        """Voice recording input area with record / pause / stop controls."""
        vc = ctk.CTkFrame(parent, fg_color=INPUT_BG, corner_radius=10,
                           border_color=BORDER, border_width=1)
        vc.grid(row=row, column=0, padx=20, pady=(4, 4), sticky="ew")
        vc.grid_columnconfigure(0, weight=1)

        self._voice_status = ctk.CTkLabel(
            vc, text="Tap the button below to start speaking your answer",
            font=("Segoe UI", 12), text_color=TEXT_DIM)
        self._voice_status.grid(row=0, column=0, pady=(20, 8))

        # Large record button
        self._rec_btn = ctk.CTkButton(
            vc, text="⬤  Start Recording",
            width=210, height=54,
            font=("Segoe UI Semibold", 14),
            fg_color=RED_DIM, hover_color=RED,
            text_color=TEXT, corner_radius=27,
            command=self._voice_start)
        self._rec_btn.grid(row=1, column=0, pady=(0, 10))

        # Pause / stop buttons
        ctrl = ctk.CTkFrame(vc, fg_color="transparent")
        ctrl.grid(row=2, column=0, pady=(0, 10))
        self._pause_btn = ctk.CTkButton(ctrl, text="⏸  Pause", width=104, height=34,
                                         font=FONT_BODY, state="disabled",
                                         fg_color="transparent", hover_color=CARD,
                                         text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                                         command=self._voice_pause)
        self._pause_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = ctk.CTkButton(ctrl, text="■  Stop & Use", width=124, height=34,
                                        font=FONT_BODY, state="disabled",
                                        fg_color="transparent", hover_color=CARD,
                                        text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                                        command=self._voice_stop)
        self._stop_btn.pack(side="left")

        # Transcription edit box
        self._voice_edit_label = ctk.CTkLabel(
            vc, text="Your transcribed answer will appear here",
            font=FONT_TINY, text_color=TEXT_DIM)
        self._voice_edit_label.grid(row=3, column=0, pady=(4, 0))

        self._voice_box = ctk.CTkTextbox(vc, height=80, font=FONT_BODY,
                                          fg_color=CARD, border_color=BORDER, border_width=1,
                                          text_color=TEXT, corner_radius=6)
        self._voice_box.grid(row=4, column=0, padx=16, pady=(4, 4), sticky="ew")
        if existing:
            self._voice_box.insert("1.0", existing)
            self._voice_edit_label.configure(
                text="Current saved answer — edit below or record a new one:")
        else:
            self._voice_box.configure(state="disabled")

        self._answer_widget = self._voice_box

        ctk.CTkButton(vc, text="✏️  Switch to text input",
                      width=160, height=26, font=FONT_TINY,
                      fg_color="transparent", hover_color=CARD, text_color=TEXT_DIM,
                      border_color=BORDER, border_width=1,
                      command=self._switch_to_text).grid(row=5, column=0, pady=(4, 18))

    def _switch_to_voice(self):
        self._input_mode = "voice"
        self._mode_btn.configure(text="🎤 Voice")
        self._load_question(self.profile.current_chapter,
                            self.profile.current_question, speak_intro=False)

    def _switch_to_text(self):
        self._input_mode = "text"
        self._mode_btn.configure(text="✏️  Text")
        self._load_question(self.profile.current_chapter,
                            self.profile.current_question, speak_intro=False)

    # ── Voice recording logic ──────────────────────────────────────────────────

    def _voice_start(self):
        global _voice_process
        if self._recording:
            return
        self._recording = True
        self._rec_btn.configure(text="● Listening...", fg_color=RED)
        self._voice_status.configure(
            text="Listening — speak clearly, then pause naturally", text_color=TEXT)
        self._pause_btn.configure(state="normal")
        self._stop_btn.configure(state="normal")
        stop_speaking()

        # Use Windows built-in Speech Recognition via PowerShell — no packages needed
        ps_script = (
            "Add-Type -AssemblyName System.Speech; "
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "$r = New-Object System.Speech.Recognition.SpeechRecognitionEngine; "
            "$r.SetInputToDefaultAudioDevice(); "
            "$g = New-Object System.Speech.Recognition.DictationGrammar; "
            "$r.LoadGrammar($g); "
            "$result = $r.Recognize([System.TimeSpan]::FromSeconds(30)); "
            "if ($result) { Write-Output $result.Text }"
        )

        def _record():
            global _voice_process
            try:
                _voice_process = _subp.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
                    stdout=_subp.PIPE, stderr=_subp.DEVNULL,
                    creationflags=_subp.CREATE_NO_WINDOW,
                    encoding="utf-8",
                )
                text, _ = _voice_process.communicate(timeout=35)
                text = (text or "").strip()
                self.after(0, lambda: self._voice_done(text))
            except Exception:
                self.after(0, lambda: self._voice_done(""))
            finally:
                _voice_process = None

        threading.Thread(target=_record, daemon=True).start()

    def _voice_done(self, text: str):
        global _voice_process
        _voice_process = None
        self._recording = False
        self._rec_btn.configure(text="⬤  Record more", fg_color=RED_DIM)
        self._pause_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")
        if text:
            self._voice_box.configure(state="normal")
            prev = self._voice_box.get("1.0", "end").strip()
            combined = (prev + " " + text).strip() if prev else text
            self._voice_box.delete("1.0", "end")
            self._voice_box.insert("1.0", combined)
            self._voice_edit_label.configure(
                text="Transcribed — edit if needed, or tap Record more to continue:")
            self._voice_status.configure(
                text="Got it. Record more to continue, or Save & Continue.",
                text_color=GREEN_LT)
        else:
            self._voice_status.configure(
                text="Nothing captured — check your microphone, or switch to text.",
                text_color=AMBER)

    def _voice_pause(self):
        global _voice_process
        self._recording = False
        if _voice_process:
            try:
                _voice_process.kill()
            except Exception:
                pass
            _voice_process = None
        self._rec_btn.configure(text="⬤  Start Recording", fg_color=RED_DIM)
        self._pause_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")
        self._voice_status.configure(text="Paused. Tap Start Recording to continue.",
                                      text_color=TEXT_DIM)

    def _voice_stop(self):
        global _voice_process
        self._recording = False
        if _voice_process:
            try:
                _voice_process.kill()
            except Exception:
                pass
            _voice_process = None
        self._rec_btn.configure(text="⬤  Start Recording", fg_color=RED_DIM)
        self._pause_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")
        self._voice_status.configure(
            text="Recording stopped. Edit below if needed, then Save & Continue.",
            text_color=TEXT_DIM)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _get_current_answer(self) -> str:
        try:
            if isinstance(self._answer_widget, ctk.CTkTextbox):
                return self._answer_widget.get("1.0", "end").strip()
            elif self._answer_widget:
                return self._answer_widget.get().strip()
        except Exception:
            pass
        return ""

    def _go_next(self):
        stop_speaking()
        ch_idx = self.profile.current_chapter
        q_idx  = self.profile.current_question
        q      = CHAPTERS[ch_idx]["questions"][q_idx]
        answer = self._get_current_answer()
        if q.get("required") and not answer:
            if self._answer_widget:
                try:
                    self._answer_widget.configure(border_color=RED)
                    self.after(800, lambda: self._answer_widget.configure(border_color=BORDER))
                except Exception:
                    pass
            return
        if answer:
            self.profile.set_answer(q["id"], answer)
        self._flash_saved()
        nq = q_idx + 1
        ch = CHAPTERS[ch_idx]
        if nq < len(ch["questions"]):
            self._load_question(ch_idx, nq)
        else:
            self._chapter_complete(ch_idx)

    def _go_prev(self):
        stop_speaking()
        self._save_current_answer()
        ch_idx = self.profile.current_chapter
        q_idx  = self.profile.current_question - 1
        if q_idx < 0:
            ch_idx -= 1
            if ch_idx < 0:
                return
            q_idx = len(CHAPTERS[ch_idx]["questions"]) - 1
        self._load_question(ch_idx, q_idx)

    def _go_skip(self):
        stop_speaking()
        ch_idx = self.profile.current_chapter
        q_idx  = self.profile.current_question
        ch     = CHAPTERS[ch_idx]
        nq     = q_idx + 1
        if nq < len(ch["questions"]):
            self._load_question(ch_idx, nq)
        else:
            self._chapter_complete(ch_idx)

    def _jump_to_chapter(self, ch_idx: int):
        if not self.profile.is_chapter_enabled(CHAPTERS[ch_idx]["id"]):
            return
        stop_speaking()
        self._save_current_answer()
        self._show_chapter_landing(ch_idx)

    def _toggle_chapter_in_sidebar(self, ch_id: str):
        if ch_id in self.profile.enabled_chapters:
            self.profile.enabled_chapters.remove(ch_id)
        else:
            self.profile.enabled_chapters.append(ch_id)
        self.profile.save()
        self._render_chapter_list()

    def _show_chapter_landing(self, ch_idx: int):
        """Replace main content with chapter detail + time/mode picker."""
        self.profile.current_chapter = ch_idx
        ch  = CHAPTERS[ch_idx]
        a, t = self.profile.chapter_counts(ch_idx)

        self._chapter_header.configure(text=ch["title"])

        for w in self._content.winfo_children():
            w.destroy()
        self._content.grid_columnconfigure(0, weight=1)

        # ── Chapter info card ──────────────────────────────────────────────
        ic = self._card(self._content, corner_radius=14)
        ic.grid(row=0, column=0, sticky="ew", padx=40, pady=(32, 16))
        ic.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ic,
                     text=f"Chapter {ch_idx + 1} of {len(CHAPTERS)}",
                     font=("Segoe UI", 10), text_color=GOLD,
                     anchor="w").grid(row=0, column=0, padx=28, pady=(22, 2), sticky="w")
        ctk.CTkLabel(ic, text=ch["title"],
                     font=("Segoe UI Bold", 26), text_color=TEXT,
                     anchor="w").grid(row=1, column=0, padx=28, sticky="w")
        if ch.get("subtitle"):
            ctk.CTkLabel(ic, text=ch["subtitle"],
                         font=("Segoe UI", 13), text_color=TEXT_DIM,
                         anchor="w").grid(row=2, column=0, padx=28, pady=(2, 0), sticky="w")
        ctk.CTkLabel(ic, text=ch["intro"],
                     font=("Segoe UI", 13), text_color=TEXT_DIM,
                     anchor="w", wraplength=560,
                     justify="left").grid(row=3, column=0, padx=28, pady=(10, 0), sticky="w")

        # Progress bar
        pf = ctk.CTkFrame(ic, fg_color="transparent")
        pf.grid(row=4, column=0, padx=28, pady=(16, 24), sticky="ew")
        pf.grid_columnconfigure(0, weight=1)
        if a == t and t > 0:
            prog_text  = f"Complete — all {t} questions answered  ✓"
            prog_color = GREEN_LT
        elif a > 0:
            prog_text  = f"{a} of {t} questions answered"
            prog_color = GOLD
        else:
            prog_text  = f"{t} questions  ·  Not started yet"
            prog_color = TEXT_DIM
        ctk.CTkLabel(pf, text=prog_text, font=("Segoe UI Semibold", 12),
                     text_color=prog_color, anchor="w").grid(row=0, column=0, sticky="w")
        pb = ctk.CTkProgressBar(pf, height=6, fg_color=BORDER,
                                 progress_color=GREEN_LT if a == t else GOLD)
        pb.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        pb.set(a / t if t else 0)

        # ── Time picker ───────────────────────────────────────────────────
        tf = ctk.CTkFrame(self._content, fg_color="transparent")
        tf.grid(row=1, column=0, sticky="ew", padx=40, pady=(4, 16))
        ctk.CTkLabel(tf, text="HOW LONG DO YOU HAVE?",
                     font=("Segoe UI Semibold", 10), text_color=TEXT_DIM,
                     anchor="w").pack(anchor="w", pady=(0, 10))
        time_row = ctk.CTkFrame(tf, fg_color="transparent")
        time_row.pack(anchor="w")
        self._time_btns   = {}
        self._sel_minutes = 10
        for lbl, mins in [("5 min", 5), ("10 min", 10), ("15 min", 15),
                           ("20 min", 20), ("30 min", 30), ("No limit", None)]:
            b = ctk.CTkButton(time_row, text=lbl, height=40, width=96,
                              font=("Segoe UI", 12),
                              fg_color=INPUT_BG, hover_color=CARD,
                              text_color=TEXT, border_color=BORDER, border_width=1,
                              command=lambda m=mins: self._pick_time(m))
            b.pack(side="left", padx=(0, 8))
            self._time_btns[mins] = b
        self._pick_time(10)

        # ── Mode selector ─────────────────────────────────────────────────
        mf = ctk.CTkFrame(self._content, fg_color="transparent")
        mf.grid(row=2, column=0, sticky="ew", padx=40, pady=(0, 20))
        ctk.CTkLabel(mf, text="HOW WOULD YOU LIKE TO ANSWER?",
                     font=("Segoe UI Semibold", 10), text_color=TEXT_DIM,
                     anchor="w").pack(anchor="w", pady=(0, 12))
        mode_row = ctk.CTkFrame(mf, fg_color="transparent")
        mode_row.pack(anchor="w")

        vc = self._card(mode_row, corner_radius=12, width=256, height=176)
        vc.pack(side="left", padx=(0, 16))
        vc.pack_propagate(False)
        ctk.CTkLabel(vc, text="🎤", font=("Segoe UI", 28)).place(x=20, y=20)
        ctk.CTkLabel(vc, text="Voice Mode",
                     font=("Segoe UI Semibold", 14), text_color=TEXT,
                     anchor="w").place(x=20, y=64)
        ctk.CTkLabel(vc, text="Speak your answers aloud",
                     font=("Segoe UI", 11), text_color=TEXT_DIM,
                     anchor="w").place(x=20, y=90)
        v_lbl   = "Select" if SR_AVAILABLE else "Unavailable"
        v_state = "normal" if SR_AVAILABLE else "disabled"
        self._voice_mode_btn = ctk.CTkButton(
            vc, text=v_lbl, height=34, width=228, font=FONT_BODY, state=v_state,
            fg_color="transparent", hover_color=CARD,
            text_color=TEXT_DIM if SR_AVAILABLE else BORDER,
            border_color=BORDER, border_width=1,
            command=lambda: self._pick_mode("voice"))
        self._voice_mode_btn.place(x=14, y=130)

        tc = self._card(mode_row, corner_radius=12, width=256, height=176,
                        border_color=GOLD)
        tc.pack(side="left")
        tc.pack_propagate(False)
        ctk.CTkLabel(tc, text="✏️", font=("Segoe UI", 28)).place(x=20, y=20)
        ctk.CTkLabel(tc, text="Text Mode",
                     font=("Segoe UI Semibold", 14), text_color=TEXT,
                     anchor="w").place(x=20, y=64)
        ctk.CTkLabel(tc, text="Type at your own pace",
                     font=("Segoe UI", 11), text_color=TEXT_DIM,
                     anchor="w").place(x=20, y=90)
        self._text_mode_btn = ctk.CTkButton(
            tc, text="Selected ✓", height=34, width=228, font=FONT_BODY,
            fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
            border_color=GOLD, border_width=1,
            command=lambda: self._pick_mode("text"))
        self._text_mode_btn.place(x=14, y=130)
        self._mode_cards  = {"voice": vc, "text": tc}
        self._input_mode  = getattr(self, "_input_mode", "text") or "text"
        # Reflect existing mode choice
        self._pick_mode(self._input_mode)

        # ── Start / Resume button ─────────────────────────────────────────
        sf = ctk.CTkFrame(self._content, fg_color="transparent")
        sf.grid(row=3, column=0, sticky="w", padx=40, pady=(0, 40))
        btn_text = "Resume this section  →" if a > 0 else "Start this section  →"
        start_q  = (self.profile.current_question
                    if ch_idx == self.profile.current_chapter else 0)
        ctk.CTkButton(sf, text=btn_text,
                      font=("Segoe UI Semibold", 15), height=52, width=260,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      command=lambda: self._begin_chapter(ch_idx, start_q)
                      ).pack(side="left", padx=(0, 14))
        if a > 0:
            ctk.CTkButton(sf, text="Review answers",
                          font=("Segoe UI", 13), height=42, width=160,
                          fg_color="transparent", hover_color=CARD,
                          text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                          command=lambda: self._load_question(ch_idx, 0, speak_intro=False)
                          ).pack(side="left", padx=(0, 14))

        # Back navigation
        ctk.CTkButton(self._content, text="← Back to section list",
                      font=("Segoe UI", 12), height=32,
                      fg_color="transparent", hover_color=CARD,
                      text_color=TEXT_DIM, border_color="transparent",
                      command=self._show_chapter_selection
                      ).grid(row=4, column=0, sticky="w", padx=36, pady=(4, 40))

        self._render_chapter_list()

    def _begin_chapter(self, ch_idx: int, start_q: int = 0):
        """Start or resume a chapter after picking time and mode."""
        if self._sel_minutes is not None:
            self._session_end_time   = datetime.now() + timedelta(minutes=self._sel_minutes)
            self._session_total_secs = float(self._sel_minutes * 60)
            if hasattr(self, "_timer_bar") and self._timer_bar.winfo_exists():
                self._timer_bar.pack(side="left", padx=(0, 14))
                self._timer_bar.set(1.0)
            self._tick_timer()
        else:
            self._session_end_time   = None
            self._session_total_secs = 0
        self._mode_btn.configure(
            text="🎤 Voice" if self._input_mode == "voice" else "✏️  Text")
        self._load_question(ch_idx, start_q, speak_intro=(start_q == 0))

    def _finished_for_today(self):
        """Save current answer and show editable draft review."""
        self._save_current_answer()
        stop_speaking()
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self._session_end_time = None
        self._show_review_edit()

    def _show_review_edit(self):
        """Show editable draft view of all answers."""
        self._chapter_header.configure(text="Review & Edit Your Draft")
        for w in self._content.winfo_children():
            w.destroy()
        self._content.grid_columnconfigure(0, weight=1)

        # Top action bar
        abar = ctk.CTkFrame(self._content, fg_color="transparent")
        abar.grid(row=0, column=0, sticky="ew", padx=40, pady=(24, 8))
        ctk.CTkLabel(abar,
                     text="Your Estate Plan Draft",
                     font=("Segoe UI Bold", 24), text_color=TEXT,
                     anchor="w").pack(side="left")
        ctk.CTkButton(abar, text="Export PDF",
                      font=("Segoe UI Semibold", 12), height=40, width=140,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      command=self._export_pdf).pack(side="right")
        ctk.CTkLabel(abar,
                     text=f"{self.profile.pct()}% complete",
                     font=("Segoe UI", 12), text_color=TEXT_DIM).pack(side="right", padx=16)

        row_idx = 1
        # Editable fields grouped by chapter
        for ch_idx, ch in enumerate(CHAPTERS):
            if not self.profile.is_chapter_enabled(ch["id"]):
                continue
            a, t = self.profile.chapter_counts(ch_idx)
            if a == 0:
                continue

            # Chapter header
            ch_hdr = ctk.CTkFrame(self._content, fg_color="transparent")
            ch_hdr.grid(row=row_idx, column=0, sticky="ew",
                        padx=40, pady=(20, 4))
            done_mark = "  ✓" if self.profile.chapter_done(ch_idx) else ""
            ctk.CTkLabel(ch_hdr,
                         text=f"Chapter {ch_idx + 1}  —  {ch['title']}{done_mark}",
                         font=("Segoe UI Semibold", 15),
                         text_color=GREEN_LT if self.profile.chapter_done(ch_idx) else GOLD,
                         anchor="w").pack(side="left")
            row_idx += 1

            for q in ch["questions"]:
                ans = self.profile.get_answer(q["id"])
                if not ans:
                    continue
                qf = self._card(self._content, corner_radius=8)
                qf.grid(row=row_idx, column=0, sticky="ew", padx=40, pady=3)
                qf.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(qf, text=q["text"],
                             font=("Segoe UI Semibold", 12), text_color=TEXT,
                             anchor="w", wraplength=620,
                             justify="left").grid(row=0, column=0,
                                                  padx=18, pady=(12, 4), sticky="w")
                tb = ctk.CTkTextbox(qf, height=60, font=FONT_BODY,
                                    fg_color=INPUT_BG, border_color=BORDER,
                                    border_width=1, text_color=TEXT, corner_radius=6)
                tb.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="ew")
                tb.insert("1.0", ans)

                def _make_saver(qid, widget):
                    def _save(e=None):
                        val = widget.get("1.0", "end").strip()
                        if val:
                            self.profile.set_answer(qid, val)
                    return _save

                tb.bind("<FocusOut>", _make_saver(q["id"], tb))
                row_idx += 1

        # Bottom actions
        ba = ctk.CTkFrame(self._content, fg_color="transparent")
        ba.grid(row=row_idx, column=0, sticky="ew", padx=40, pady=(24, 48))
        ctk.CTkButton(ba, text="← Back to Interview",
                      font=FONT_BODY, height=40, width=200,
                      fg_color="transparent", hover_color=CARD,
                      text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                      command=lambda: self._show_chapter_landing(
                          self.profile.current_chapter)).pack(side="left", padx=(0, 12))
        ctk.CTkButton(ba, text="Export PDF",
                      font=("Segoe UI Semibold", 12), height=40, width=160,
                      fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                      command=self._export_pdf).pack(side="left")
        note = ctk.CTkFrame(ba, fg_color="transparent")
        note.pack(side="right")
        ctk.CTkLabel(note,
                     text="Need to open in Word?  LibreOffice is free.",
                     font=("Segoe UI", 11), text_color=TEXT_DIM).pack()
        ctk.CTkLabel(note,
                     text="libreoffice.org",
                     font=("Segoe UI", 11), text_color=GOLD).pack()

        self._render_chapter_list()
        self._update_progress()

    # ── Chapter complete ───────────────────────────────────────────────────────

    def _chapter_complete(self, ch_idx: int):
        stop_speaking()
        ch = CHAPTERS[ch_idx]
        for w in self._content.winfo_children():
            w.destroy()
        card = self._card(self._content, border_color=GOLD, corner_radius=14)
        card.grid(row=0, column=0, sticky="nsew", padx=60, pady=60)
        self._content.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="✓", font=("Segoe UI", 52),
                     text_color=GOLD).grid(pady=(44, 8))
        ctk.CTkLabel(card, text=ch["title"],
                     font=("Segoe UI Bold", 24), text_color=TEXT).grid()
        ctk.CTkLabel(card, text="Complete",
                     font=("Segoe UI", 14), text_color=GOLD).grid(pady=(0, 16))
        ctk.CTkLabel(card, text=ch["complete_message"],
                     font=("Segoe UI", 13), text_color=TEXT_DIM,
                     wraplength=480, justify="center").grid(padx=40, pady=(0, 24))
        ctk.CTkLabel(card, text=f"{self.profile.pct()}% of your estate plan is complete.",
                     font=("Segoe UI Semibold", 12), text_color=TEXT).grid(pady=(0, 8))
        pb = ctk.CTkProgressBar(card, height=8, fg_color=BORDER,
                                 progress_color=GOLD, width=360)
        pb.grid(pady=(0, 32))
        pb.set(self.profile.pct() / 100)

        next_ch = self.profile.next_enabled_chapter(ch_idx)
        if next_ch is not None:
            ctk.CTkButton(card,
                          text=f"Continue to {CHAPTERS[next_ch]['title']}  →",
                          font=("Segoe UI Semibold", 13), height=46, width=320,
                          fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                          command=lambda: self._load_question(next_ch, 0, speak_intro=True)
                          ).grid(pady=(0, 12))
        else:
            ctk.CTkLabel(card, text="Your plan is complete.",
                         font=("Segoe UI Bold", 16), text_color=GREEN_LT).grid(pady=(0, 12))
            ctk.CTkButton(card, text="Export PDF",
                          font=("Segoe UI Semibold", 14), height=48, width=300,
                          fg_color=GOLD, hover_color=GOLD_HOVER, text_color="#0D1117",
                          command=self._export_pdf).grid(pady=(0, 12))

        ctk.CTkButton(card, text="✔  Done for Today — save & review draft",
                      font=("Segoe UI", 12), height=36,
                      fg_color="transparent", hover_color=CARD, text_color=GREEN,
                      border_color=GREEN, border_width=1,
                      command=self._finished_for_today).grid(pady=(0, 40))

        self._chapter_header.configure(text=f"{ch['title']}  —  Complete")
        self._render_chapter_list()
        self._update_progress()
        if not self.muted:
            speak(ch["complete_message"])

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _update_progress(self):
        pct = self.profile.pct()
        self._pct_label.configure(text=f"{pct}% complete")
        self._progress_bar.set(pct / 100)

    def _flash_saved(self):
        self._save_label.configure(text="Saved ✓", text_color=GREEN_LT)
        self.after(2000, lambda: self._save_label.configure(text=""))

    def _toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            stop_speaking()
            self._mute_btn.configure(text="🔇 Voice off")
        else:
            self._mute_btn.configure(text="🔊 Voice on")

    def _export_pdf(self):
        stop_speaking()
        default_name = f"{self.profile.name.replace(' ', '_')}_EstatePlan.pdf"
        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=default_name,
            title="Save Estate Plan PDF",
        )
        if not out_path:
            return
        try:
            data = json.loads(self.profile.filepath.read_text(encoding="utf-8"))
            generate_pdf(data, Path(out_path))
            messagebox.showinfo(
                "Export complete",
                f"Estate plan saved to:\n{out_path}\n\n"
                "Print one copy for your fireproof safe and\n"
                "give one copy to your executor.\n\n"
                "To edit this document, open it in any PDF viewer.\n"
                "For a free Word-compatible editor, visit libreoffice.org"
            )
        except Exception as e:
            messagebox.showerror("Export failed", str(e))


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = EstateInterviewApp()
    app.mainloop()
