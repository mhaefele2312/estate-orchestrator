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
from datetime import datetime
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
        if not self.enabled_chapters:
            return sum(1 for v in self.answers.values() if str(v).strip())
        enabled_qids = {q["id"] for ch in CHAPTERS
                        if ch["id"] in self.enabled_chapters
                        for q in ch["questions"]}
        return sum(1 for qid, v in self.answers.items()
                   if qid in enabled_qids and str(v).strip())

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
                       border_color=GOLD if active else PANEL, border_width=1 if active else 0)
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
        self._form_fields:       dict  = {}    # q_id -> widget in current form
        self._focused_qid:       str   = ""    # q_id of currently focused field
        self._voice_flow:        int   = 0     # questions remaining in voice flow batch
        self._flow_auto_id             = None  # after() id for auto-record delay

        self._show_start()

    # ── Utility ────────────────────────────────────────────────────────────────

    def _clear(self):
        stop_speaking()
        self._voice_flow = 0
        if self._flow_auto_id:
            self.after_cancel(self._flow_auto_id)
            self._flow_auto_id = None
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

        ctk.CTkButton(scroll, text="Begin My Estate Plan  ->",
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
            ctk.CTkButton(row, text="Continue ->", width=130, height=38,
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
        self._show_interview()

    def _load_profile(self, name: str):
        self.profile = Profile(name)
        self._show_interview()

    # ─────────────────────────────────────────────────────────────────────────
    # SCREEN 2 — Interview (sidebar + main panel)
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
        self._show_chapter_form(ch_idx)

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
        nav.grid_columnconfigure(2, weight=1)

        self._prev_btn = ctk.CTkButton(nav, text="<- Previous Chapter", width=170, height=38,
                                        fg_color="transparent", hover_color=CARD,
                                        text_color=TEXT_DIM, font=FONT_BODY,
                                        border_color=BORDER, border_width=1,
                                        command=self._go_prev_chapter)
        self._prev_btn.grid(row=0, column=0, padx=(22, 8), pady=12)

        # ── Mic controls in footer
        if SR_AVAILABLE:
            mic_frame = ctk.CTkFrame(nav, fg_color="transparent")
            mic_frame.grid(row=0, column=1, padx=4, pady=12)

            self._footer_rec_btn = ctk.CTkButton(
                mic_frame, text="Record", width=90, height=36,
                font=("Segoe UI Semibold", 11),
                fg_color=RED_DIM, hover_color=RED, text_color="#FFFFFF",
                corner_radius=18, command=self._footer_mic_start)
            self._footer_rec_btn.pack(side="left", padx=(0, 4))

            self._footer_stop_btn = ctk.CTkButton(
                mic_frame, text="Stop", width=60, height=36,
                font=("Segoe UI", 11), state="disabled",
                fg_color="transparent", hover_color=CARD,
                text_color=TEXT_DIM, border_color=BORDER, border_width=1,
                corner_radius=18, command=self._footer_mic_stop)
            self._footer_stop_btn.pack(side="left", padx=(0, 4))

            self._mic_label = ctk.CTkLabel(
                mic_frame, text="Click a field, then Record",
                font=("Segoe UI", 10), text_color=TEXT_DIM, width=160)
            self._mic_label.pack(side="left", padx=(4, 0))

        self._save_label = ctk.CTkLabel(nav, text="", font=FONT_TINY, text_color=TEXT_DIM)
        self._save_label.grid(row=0, column=2)

        self._next_btn = ctk.CTkButton(nav, text="Next Chapter  ->",
                                        width=170, height=38,
                                        fg_color=GOLD, hover_color=GOLD_HOVER,
                                        text_color="#0D1117",
                                        font=("Segoe UI Semibold", 12),
                                        command=self._go_next_chapter)
        self._next_btn.grid(row=0, column=3, padx=(8, 22), pady=12)

    # ── Chapter form (all questions for a chapter) ─────────────────────────────

    def _show_chapter_form(self, ch_idx: int):
        """Show all questions for this chapter as a scrollable form."""
        stop_speaking()
        self._voice_flow = 0
        if self._flow_auto_id:
            self.after_cancel(self._flow_auto_id)
            self._flow_auto_id = None

        ch_idx = max(0, min(ch_idx, len(CHAPTERS) - 1))
        self.profile.current_chapter = ch_idx
        self.profile.save()

        ch   = CHAPTERS[ch_idx]
        a, t = self.profile.chapter_counts(ch_idx)

        self._chapter_header.configure(
            text=f"Chapter {ch_idx + 1}  —  {ch['title']}  ({a}/{t} answered)")

        for w in self._content.winfo_children():
            w.destroy()
        self._content.grid_columnconfigure(0, weight=1)

        # Track all field widgets for saving
        self._form_fields = {}  # q_id -> widget

        row = 0

        # ── Chapter intro card ────────────────────────────────────────────
        ic = self._card(self._content, corner_radius=12)
        ic.grid(row=row, column=0, sticky="ew", padx=28, pady=(20, 8))
        ic.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ic,
                     text=f"Chapter {ch_idx + 1} of {len(CHAPTERS)}",
                     font=("Segoe UI", 10), text_color=GOLD,
                     anchor="w").grid(row=0, column=0, padx=20, pady=(14, 2), sticky="w")
        ctk.CTkLabel(ic, text=ch["title"],
                     font=("Segoe UI Bold", 22), text_color=TEXT,
                     anchor="w").grid(row=1, column=0, padx=20, sticky="w")
        ctk.CTkLabel(ic, text=ch["intro"],
                     font=("Segoe UI", 12), text_color=TEXT_DIM,
                     anchor="w", justify="left", wraplength=620).grid(
            row=2, column=0, padx=20, pady=(4, 14), sticky="w")

        # Voice flow buttons
        if SR_AVAILABLE and t > 1:
            vf = ctk.CTkFrame(ic, fg_color="transparent")
            vf.grid(row=3, column=0, padx=20, pady=(0, 14), sticky="w")
            unanswered = t - a
            if unanswered > 0:
                flow_count = min(unanswered, 5) if unanswered >= 5 else unanswered
                ctk.CTkButton(vf, text=f"🎤  Answer {flow_count} by Voice",
                              font=("Segoe UI Semibold", 11), height=36, width=200,
                              fg_color="#1e3a5f", hover_color="#163050",
                              text_color="#bfdbfe", corner_radius=8,
                              command=lambda: self._start_voice_flow(ch_idx, flow_count)
                              ).pack(side="left", padx=(0, 10))
                if unanswered > 5:
                    ctk.CTkButton(vf, text=f"🎤  All {unanswered} unanswered",
                                  font=("Segoe UI Semibold", 11), height=36, width=200,
                                  fg_color="#1e3a5f", hover_color="#163050",
                                  text_color="#bfdbfe", corner_radius=8,
                                  command=lambda: self._start_voice_flow(ch_idx, unanswered)
                                  ).pack(side="left")

        row += 1

        # ── Question fields ───────────────────────────────────────────────
        for qi, q in enumerate(ch["questions"]):
            existing = self.profile.get_answer(q["id"])

            qf = self._card(self._content, corner_radius=8)
            qf.grid(row=row, column=0, sticky="ew", padx=28, pady=4)
            qf.grid_columnconfigure(0, weight=1)

            # Question label row
            lbl_row = ctk.CTkFrame(qf, fg_color="transparent")
            lbl_row.grid(row=0, column=0, padx=16, pady=(12, 2), sticky="ew")
            lbl_row.grid_columnconfigure(0, weight=1)

            q_text = q["text"]
            if q.get("required"):
                q_text += "  *"
            ctk.CTkLabel(lbl_row, text=q_text,
                         font=("Segoe UI Semibold", 12), text_color=TEXT,
                         anchor="w", wraplength=580, justify="left").grid(
                row=0, column=0, sticky="w")

            # Help text
            if q.get("help"):
                ctk.CTkLabel(qf, text=q["help"],
                             font=("Segoe UI", 10), text_color=TEXT_DIM,
                             anchor="w").grid(row=1, column=0, padx=16, sticky="w")

            # Focus tracker — so footer mic knows which field to record into
            def _make_focus_tracker(qid):
                def _on_focus(e=None):
                    self._focused_qid = qid
                    self._update_mic_label()
                return _on_focus

            # Input field
            if q["type"] == "multiline":
                widget = ctk.CTkTextbox(
                    qf, height=90, font=FONT_BODY,
                    fg_color=INPUT_BG, border_color=BORDER, border_width=1,
                    text_color=TEXT, corner_radius=6)
                widget.grid(row=2, column=0, padx=12, pady=(4, 12), sticky="ew")
                if existing:
                    widget.insert("1.0", existing)

                def _make_saver_tb(qid, w):
                    def _save(e=None):
                        val = w.get("1.0", "end").strip()
                        self.profile.set_answer(qid, val)
                        self._update_header_counts()
                    return _save
                widget.bind("<FocusOut>", _make_saver_tb(q["id"], widget))
                widget.bind("<FocusIn>", _make_focus_tracker(q["id"]))
            else:
                widget = ctk.CTkEntry(
                    qf, height=40, font=FONT_BODY,
                    placeholder_text=q.get("placeholder", ""),
                    fg_color=INPUT_BG, border_color=BORDER, border_width=1,
                    text_color=TEXT, corner_radius=6)
                widget.grid(row=2, column=0, padx=12, pady=(4, 12), sticky="ew")
                if existing:
                    widget.insert(0, existing)

                def _make_saver_entry(qid, w):
                    def _save(e=None):
                        val = w.get().strip()
                        self.profile.set_answer(qid, val)
                        self._update_header_counts()
                    return _save
                widget.bind("<FocusOut>", _make_saver_entry(q["id"], widget))
                widget.bind("<FocusIn>", _make_focus_tracker(q["id"]))

            self._form_fields[q["id"]] = widget
            row += 1

        # ── Bottom padding ────────────────────────────────────────────────
        ctk.CTkFrame(self._content, fg_color="transparent", height=20).grid(
            row=row, column=0)

        # ── Update nav buttons ────────────────────────────────────────────
        enabled = self.profile.enabled_indices()
        ch_pos  = enabled.index(ch_idx) if ch_idx in enabled else 0
        self._prev_btn.configure(
            state="normal" if ch_pos > 0 else "disabled")
        if ch_pos < len(enabled) - 1:
            next_name = CHAPTERS[enabled[ch_pos + 1]]["title"]
            self._next_btn.configure(text=f"{next_name}  ->")
        else:
            self._next_btn.configure(text="Export PDF  ->")

        self._render_chapter_list()
        self._update_progress()

    def _update_header_counts(self):
        """Update the top bar with current answer counts after a field save."""
        ch_idx = self.profile.current_chapter
        ch     = CHAPTERS[ch_idx]
        a, t   = self.profile.chapter_counts(ch_idx)
        self._chapter_header.configure(
            text=f"Chapter {ch_idx + 1}  —  {ch['title']}  ({a}/{t} answered)")
        self._update_progress()
        self._flash_saved()

    def _save_all_form_fields(self):
        """Save every field in the current form to the profile."""
        for qid, widget in self._form_fields.items():
            try:
                if isinstance(widget, ctk.CTkTextbox):
                    val = widget.get("1.0", "end").strip()
                else:
                    val = widget.get().strip()
                if val:
                    self.profile.set_answer(qid, val)
            except Exception:
                pass

    # ── Voice flow (within form) ──────────────────────────────────────────────

    def _start_voice_flow(self, ch_idx: int, count: int):
        """Start voice flow through unanswered questions in the current chapter."""
        ch = CHAPTERS[ch_idx]
        # Find first unanswered question
        for qi, q in enumerate(ch["questions"]):
            if not self.profile.get_answer(q["id"]).strip():
                self._voice_flow = count
                self._voice_flow_chapter = ch_idx
                self._voice_flow_q_index = qi
                self._voice_flow_ask_next()
                return

    def _voice_flow_ask_next(self):
        """Ask the next unanswered question via TTS then record."""
        if self._voice_flow <= 0:
            return

        ch = CHAPTERS[self._voice_flow_chapter]
        questions = ch["questions"]

        # Find next unanswered from current position
        while self._voice_flow_q_index < len(questions):
            q = questions[self._voice_flow_q_index]
            if not self.profile.get_answer(q["id"]).strip():
                break
            self._voice_flow_q_index += 1
        else:
            # No more unanswered
            self._voice_flow = 0
            self._show_chapter_form(self._voice_flow_chapter)
            return

        q = questions[self._voice_flow_q_index]

        # Speak the question
        if not self.muted:
            speak(q["voice"])

        # Show a recording overlay
        self._show_voice_overlay(q)

    def _show_voice_overlay(self, q):
        """Show a voice recording popup over the form."""
        # Create overlay frame at top of content
        self._voice_overlay = ctk.CTkFrame(self._content, fg_color="#1e3a5f",
                                            corner_radius=12, border_color=GOLD,
                                            border_width=2)
        self._voice_overlay.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 8))
        self._voice_overlay.grid_columnconfigure(0, weight=1)
        self._voice_overlay.lift()

        ctk.CTkLabel(self._voice_overlay,
                     text=f"🎤  Voice Flow — {self._voice_flow} remaining",
                     font=("Segoe UI Semibold", 11), text_color="#bfdbfe",
                     anchor="w").grid(row=0, column=0, padx=20, pady=(14, 4), sticky="w")

        ctk.CTkLabel(self._voice_overlay, text=q["text"],
                     font=("Segoe UI Bold", 16), text_color="#FFFFFF",
                     anchor="w", wraplength=560, justify="left").grid(
            row=1, column=0, padx=20, pady=(0, 4), sticky="w")

        self._voice_status = ctk.CTkLabel(self._voice_overlay,
                     text="Listening after the voice finishes reading...",
                     font=("Segoe UI", 12), text_color="#93c5fd")
        self._voice_status.grid(row=2, column=0, padx=20, pady=(4, 4), sticky="w")

        self._voice_box = ctk.CTkTextbox(self._voice_overlay, height=60, font=FONT_BODY,
                                          fg_color="#0f2036", border_color="#334155",
                                          border_width=1, text_color="#e2e8f0",
                                          corner_radius=6)
        self._voice_box.grid(row=3, column=0, padx=16, pady=(4, 4), sticky="ew")
        self._voice_box.configure(state="disabled")

        btn_row = ctk.CTkFrame(self._voice_overlay, fg_color="transparent")
        btn_row.grid(row=4, column=0, padx=16, pady=(4, 14))

        self._rec_btn = ctk.CTkButton(btn_row, text="⬤  Start Recording",
                     width=180, height=44, font=("Segoe UI Semibold", 13),
                     fg_color=RED_DIM, hover_color=RED, text_color="#FFFFFF",
                     corner_radius=22, command=self._voice_start)
        self._rec_btn.pack(side="left", padx=(0, 10))

        self._pause_btn = ctk.CTkButton(btn_row, text="⏸  Pause", width=90, height=36,
                     font=FONT_BODY, state="disabled",
                     fg_color="transparent", hover_color="#163050",
                     text_color="#93c5fd", border_color="#334155", border_width=1,
                     command=self._voice_pause)
        self._pause_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="Stop Flow", width=90, height=36,
                     font=FONT_BODY,
                     fg_color="transparent", hover_color="#163050",
                     text_color="#93c5fd", border_color="#334155", border_width=1,
                     command=self._stop_voice_flow_and_refresh
                     ).pack(side="left")

        # Auto-start recording after TTS delay
        delay = 4000 if not self.muted else 500
        if self._flow_auto_id:
            self.after_cancel(self._flow_auto_id)
        self._flow_auto_id = self.after(delay, self._flow_auto_record)

    def _flow_auto_record(self):
        """Called by after() to auto-start recording during voice flow."""
        self._flow_auto_id = None
        if self._voice_flow > 0 and not self._recording:
            self._voice_start()

    def _stop_voice_flow_and_refresh(self):
        """Stop voice flow and refresh the chapter form."""
        self._voice_flow = 0
        if self._flow_auto_id:
            self.after_cancel(self._flow_auto_id)
            self._flow_auto_id = None
        stop_speaking()
        self._show_chapter_form(self.profile.current_chapter)

    # ── Voice recording logic ──────────────────────────────────────────────────

    def _voice_start(self):
        global _voice_process
        if self._recording:
            return
        self._recording = True
        self._rec_btn.configure(text="● Listening...", fg_color=RED)
        self._voice_status.configure(
            text="Listening — speak clearly, then pause naturally", text_color="#93c5fd")
        self._pause_btn.configure(state="normal")
        stop_speaking()

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
        self._rec_btn.configure(text="⬤  Record Again", fg_color=RED_DIM)
        self._pause_btn.configure(state="disabled")

        if text:
            self._voice_box.configure(state="normal")
            prev = self._voice_box.get("1.0", "end").strip()
            combined = (prev + " " + text).strip() if prev else text
            self._voice_box.delete("1.0", "end")
            self._voice_box.insert("1.0", combined)
            self._voice_status.configure(
                text="Got it. Recording again, or moving to next...",
                text_color="#86efac")

            # Save the answer
            if self._voice_flow > 0:
                ch = CHAPTERS[self._voice_flow_chapter]
                q  = ch["questions"][self._voice_flow_q_index]
                self.profile.set_answer(q["id"], combined)
                self._voice_flow -= 1
                self._voice_flow_q_index += 1
                if self._voice_flow > 0:
                    self.after(1500, self._voice_flow_next_or_done)
                else:
                    self._voice_status.configure(
                        text="Voice flow complete. All answers saved.",
                        text_color="#86efac")
                    self.after(1500, lambda: self._show_chapter_form(
                        self._voice_flow_chapter))
        else:
            self._voice_status.configure(
                text="Nothing captured — try again or click Stop Flow.",
                text_color="#fbbf24")
            if self._voice_flow > 0:
                self._voice_flow = 0
                self.after(2000, lambda: self._show_chapter_form(
                    self.profile.current_chapter))

    def _voice_flow_next_or_done(self):
        """Move to next unanswered question in voice flow."""
        if self._voice_flow <= 0:
            self._show_chapter_form(self.profile.current_chapter)
            return
        # Remove overlay and ask next
        try:
            self._voice_overlay.destroy()
        except Exception:
            pass
        self._voice_flow_ask_next()

    def _voice_pause(self):
        global _voice_process
        self._voice_flow = 0
        self._recording = False
        if _voice_process:
            try:
                _voice_process.kill()
            except Exception:
                pass
            _voice_process = None
        self._rec_btn.configure(text="⬤  Start Recording", fg_color=RED_DIM)
        self._pause_btn.configure(state="disabled")
        self._voice_status.configure(text="Paused. Voice flow stopped.",
                                      text_color="#93c5fd")
        self.after(1500, lambda: self._show_chapter_form(
            self.profile.current_chapter))

    # ── Footer mic (record into focused field) ──────────────────────────────

    def _update_mic_label(self):
        """Update the mic label to show which field will receive dictation."""
        if not SR_AVAILABLE or not hasattr(self, '_mic_label'):
            return
        if self._focused_qid and self._focused_qid in self._form_fields:
            # Find the question label
            ch = CHAPTERS[self.profile.current_chapter]
            for q in ch["questions"]:
                if q["id"] == self._focused_qid:
                    short = q["label"][:25]
                    self._mic_label.configure(text=f"Field: {short}",
                                               text_color=TEXT)
                    return
        self._mic_label.configure(text="Click a field, then Record",
                                   text_color=TEXT_DIM)

    def _footer_mic_start(self):
        """Start recording into the currently focused form field."""
        global _voice_process
        if self._recording:
            return
        if not self._focused_qid or self._focused_qid not in self._form_fields:
            self._mic_label.configure(text="Click a field first!",
                                       text_color=RED)
            self.after(2000, self._update_mic_label)
            return

        self._recording = True
        self._footer_rec_btn.configure(text="Listening...", fg_color=RED)
        self._footer_stop_btn.configure(state="normal")
        self._mic_label.configure(text="Speak now...", text_color=RED)
        stop_speaking()

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
                self.after(0, lambda: self._footer_mic_done(text))
            except Exception:
                self.after(0, lambda: self._footer_mic_done(""))
            finally:
                _voice_process = None

        threading.Thread(target=_record, daemon=True).start()

    def _footer_mic_done(self, text: str):
        """Handle completed footer mic recording — insert text into focused field."""
        global _voice_process
        _voice_process = None
        self._recording = False
        self._footer_rec_btn.configure(text="Record", fg_color=RED_DIM)
        self._footer_stop_btn.configure(state="disabled")

        qid = self._focused_qid
        if not text:
            self._mic_label.configure(text="Nothing captured. Try again.",
                                       text_color=AMBER)
            self.after(2000, self._update_mic_label)
            return

        if qid not in self._form_fields:
            self._mic_label.configure(text="Field gone. Click another.",
                                       text_color=AMBER)
            self.after(2000, self._update_mic_label)
            return

        widget = self._form_fields[qid]
        if isinstance(widget, ctk.CTkTextbox):
            prev = widget.get("1.0", "end").strip()
            combined = (prev + " " + text).strip() if prev else text
            widget.delete("1.0", "end")
            widget.insert("1.0", combined)
        else:
            prev = widget.get().strip()
            combined = (prev + " " + text).strip() if prev else text
            widget.delete(0, "end")
            widget.insert(0, combined)

        # Auto-save
        self.profile.set_answer(qid, combined)
        self._update_header_counts()
        self._mic_label.configure(text="Saved. Record more or click next field.",
                                   text_color=GREEN_LT)
        self.after(3000, self._update_mic_label)

    def _footer_mic_stop(self):
        """Stop an in-progress footer mic recording."""
        global _voice_process
        self._recording = False
        if _voice_process:
            try:
                _voice_process.kill()
            except Exception:
                pass
            _voice_process = None
        self._footer_rec_btn.configure(text="Record", fg_color=RED_DIM)
        self._footer_stop_btn.configure(state="disabled")
        self._mic_label.configure(text="Stopped.", text_color=TEXT_DIM)
        self.after(2000, self._update_mic_label)

    # ── Chapter navigation ────────────────────────────────────────────────────

    def _go_next_chapter(self):
        """Save all fields and go to the next enabled chapter."""
        stop_speaking()
        self._save_all_form_fields()
        enabled = self.profile.enabled_indices()
        ch_idx  = self.profile.current_chapter
        ch_pos  = enabled.index(ch_idx) if ch_idx in enabled else 0
        if ch_pos < len(enabled) - 1:
            self._show_chapter_form(enabled[ch_pos + 1])
        else:
            # Last chapter — export PDF
            self._export_pdf()

    def _go_prev_chapter(self):
        """Save all fields and go to the previous enabled chapter."""
        stop_speaking()
        self._save_all_form_fields()
        enabled = self.profile.enabled_indices()
        ch_idx  = self.profile.current_chapter
        ch_pos  = enabled.index(ch_idx) if ch_idx in enabled else 0
        if ch_pos > 0:
            self._show_chapter_form(enabled[ch_pos - 1])

    def _jump_to_chapter(self, ch_idx: int):
        if not self.profile.is_chapter_enabled(CHAPTERS[ch_idx]["id"]):
            return
        stop_speaking()
        self._save_all_form_fields()
        self._show_chapter_form(ch_idx)

    def _toggle_chapter_in_sidebar(self, ch_id: str):
        if ch_id in self.profile.enabled_chapters:
            self.profile.enabled_chapters.remove(ch_id)
        else:
            self.profile.enabled_chapters.append(ch_id)
        self.profile.save()
        self._render_chapter_list()

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
