"""app.py — UESDKGenApp GUI for UESDKGen.

All UI code lives here.  Business logic is delegated to:
  backends.py   — memory back-ends
  reader.py     — UE3Reader
  profiles.py   — GAME_PROFILES
  codegen.py    — generate_sdk()
  theme.py      — C palette, apply_theme()
  bruteforce.py — BruteForcer (automated discovery)
"""
from __future__ import annotations

import datetime
import io
import json
import pathlib
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Tuple

try:
    from .theme      import C, apply_theme
    from .backends   import MemoryBackend, NativeBackend, VmmBackend, SocketDMABackend, list_procs
    from .reader     import UE3Reader, PatternScanner
    from .profiles   import GAME_PROFILES, PROFILE_KEYS, DEFAULT_PROFILE
    from .codegen    import generate_sdk
    from .bruteforce import BruteForcer
except ImportError:
    from theme      import C, apply_theme          # type: ignore[no-redef]
    from backends   import (MemoryBackend, NativeBackend, VmmBackend,  # type: ignore[no-redef]
                            SocketDMABackend, list_procs)
    from reader     import UE3Reader, PatternScanner       # type: ignore[no-redef]
    from profiles   import GAME_PROFILES, PROFILE_KEYS, DEFAULT_PROFILE  # type: ignore[no-redef]
    from codegen    import generate_sdk            # type: ignore[no-redef]
    from bruteforce import BruteForcer             # type: ignore[no-redef]


class UESDKGenApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("UE3 SDK Generator")
        self.geometry("1400x900")
        self.configure(bg=C["base"])
        self.minsize(1080, 680)
        apply_theme(self)

        self._backend: Optional[MemoryBackend] = None
        self._reader:  Optional[UE3Reader]      = None
        self._names:   Dict[int, str]           = {}
        self._objects: List[Dict]               = []
        self._procs:   List[Tuple[int, str]]    = []
        self._bf_best_result: Optional[Dict]    = None   # last discovery result

        # ── sidebar variables ─────────────────────────────────────────────
        self._var_profile    = tk.StringVar(value=DEFAULT_PROFILE)
        self._var_gobjects   = tk.StringVar(value="0x013B9B78")
        self._var_gnames     = tk.StringVar(value="0x01377868")
        self._var_nameoff    = tk.StringVar(value="0x2C")
        self._var_namestroff = tk.StringVar(value="0x10")
        self._var_64bit      = tk.BooleanVar(value=False)
        self._var_mode       = tk.StringVar(value="native")  # native|dma_vmm|dma_tcp
        self._var_proc_flt   = tk.StringVar()
        self._var_proc_flt.trace_add("write", lambda *_: self._filter_procs())
        self._var_vmm_device = tk.StringVar(value="fpga")
        self._var_vmm_proc   = tk.StringVar(value="UDKGame-Win32-Shipping.exe")
        self._var_tcp_host   = tk.StringVar(value="127.0.0.1")
        self._var_tcp_port   = tk.StringVar(value="8765")
        self._var_tcp_proc   = tk.StringVar(value="UDKGame-Win32-Shipping.exe")
        self._var_tcp_token  = tk.StringVar(value="")

        # ── SDK tab variables ─────────────────────────────────────────────
        self._var_sdk_lang   = tk.StringVar(value="cpp")   # cpp|python
        self._var_sdk_target = tk.StringVar(value="both")  # native|dma|both

        self._build_ui()
        self._refresh_procs()
        self._load_profile(DEFAULT_PROFILE)

    # ═══════════════════════════════════════════════════════════════════════
    # UI construction
    # ═══════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        # header bar
        hdr = tk.Frame(self, bg=C["crust"], height=38)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  UE3 SDK Generator",
                 bg=C["crust"], fg=C["mauve"],
                 font=("Consolas", 12, "bold")).pack(side="left", padx=8)
        tk.Label(hdr,
                 text="Native  |  DMA/PCILeech  |  DMA/TCP  ·  "
                      "GNames  GObjects  C++ SDK  Python SDK",
                 bg=C["crust"], fg=C["subtext0"],
                 font=("Consolas", 9)).pack(side="left")

        body = tk.Frame(self, bg=C["base"])
        body.pack(fill="both", expand=True)

        self._sidebar = tk.Frame(body, bg=C["mantle"], width=320)
        self._sidebar.pack(fill="y", side="left")
        self._sidebar.pack_propagate(False)

        content = tk.Frame(body, bg=C["base"])
        content.pack(fill="both", expand=True, side="left")

        self._build_sidebar()
        self._build_content(content)

        # status bar
        sb = tk.Frame(self, bg=C["crust"], height=26)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self._status_var = tk.StringVar(value="Ready — select a profile and attach")
        tk.Label(sb, textvariable=self._status_var,
                 bg=C["crust"], fg=C["subtext0"],
                 font=("Consolas", 9), anchor="w").pack(
                 side="left", fill="x", expand=True, padx=8)
        self._conn_dot = tk.Label(sb, text="[x] Detached",
                                   bg=C["crust"], fg=C["red"],
                                   font=("Consolas", 9))
        self._conn_dot.pack(side="right", padx=10)

    # ── sidebar ──────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        p = self._sidebar

        # game profile picker
        pf = ttk.LabelFrame(p, text=" Game Profile ")
        pf.pack(fill="x", padx=8, pady=(10, 4))
        profile_cb = ttk.Combobox(pf, textvariable=self._var_profile,
                                   values=PROFILE_KEYS, state="readonly", width=26)
        profile_cb.pack(padx=6, pady=(4, 2), fill="x")
        # Explicitly set the current item so the text is visible after theme application
        if DEFAULT_PROFILE in PROFILE_KEYS:
            profile_cb.current(PROFILE_KEYS.index(DEFAULT_PROFILE))
        profile_cb.bind("<<ComboboxSelected>>",
                        lambda e: self._load_profile(self._var_profile.get()))
        # UE version badge
        self._ue_badge = tk.Label(pf, text="UE3", font=("Consolas", 8, "bold"),
                                   fg="#1e1e2e", bg="#89b4fa", relief="flat",
                                   padx=4, pady=1)
        self._ue_badge.pack(anchor="e", padx=6, pady=(0, 4))

        # connection mode
        mf = ttk.LabelFrame(p, text=" Connection Mode ")
        mf.pack(fill="x", padx=8, pady=4)
        for val, label in [
            ("native",  "Native  (ReadProcessMemory)"),
            ("dma_vmm", "DMA  /  PCILeech  (memprocfs)"),
            ("dma_tcp", "DMA  /  TCP bridge server"),
        ]:
            ttk.Radiobutton(mf, text=label,
                            variable=self._var_mode, value=val,
                            command=self._on_mode_change).pack(
                            anchor="w", padx=8, pady=2)

        # Native process list
        self._native_frame = ttk.LabelFrame(p, text=" Process (Native) ")
        self._native_frame.pack(fill="x", padx=8, pady=4)

        flt_row = tk.Frame(self._native_frame, bg=C["base"])
        flt_row.pack(fill="x", padx=4, pady=(4, 2))
        ttk.Entry(flt_row, textvariable=self._var_proc_flt, width=18).pack(
            side="left", fill="x", expand=True)
        ttk.Button(flt_row, text="R", width=3,
                   command=self._refresh_procs).pack(side="right", padx=(2, 0))

        lb_frame = tk.Frame(self._native_frame, bg=C["mantle"])
        lb_frame.pack(fill="x", padx=4, pady=2)
        lb_sb = ttk.Scrollbar(lb_frame, orient="vertical")
        self._proc_lb = tk.Listbox(
            lb_frame, height=7,
            bg=C["mantle"], fg=C["text"],
            selectbackground=C["blue"], selectforeground=C["base"],
            font=("Consolas", 9), borderwidth=0, highlightthickness=0,
            activestyle="none", yscrollcommand=lb_sb.set)
        lb_sb.config(command=self._proc_lb.yview)
        self._proc_lb.pack(side="left", fill="x", expand=True)
        lb_sb.pack(side="right", fill="y")
        # When a process is clicked, auto-fill the process-name fields
        self._proc_lb.bind("<<ListboxSelect>>", self._on_proc_select)

        # DMA PCILeech / memprocfs config
        self._vmm_frame = ttk.LabelFrame(p, text=" DMA / PCILeech (memprocfs) ")
        self._vmm_frame.pack(fill="x", padx=8, pady=4)
        for label, var in [
            ("LeechCore device:", self._var_vmm_device),
            ("Process name:",     self._var_vmm_proc),
        ]:
            row = tk.Frame(self._vmm_frame, bg=C["base"])
            row.pack(fill="x", padx=6, pady=2)
            tk.Label(row, text=label, bg=C["base"], fg=C["subtext0"],
                     font=("Consolas", 8), anchor="w", width=19).pack(side="left")
            ttk.Entry(row, textvariable=var, font=("Consolas", 9)).pack(
                side="left", fill="x", expand=True)
        tk.Label(self._vmm_frame,
                 text="  Not installed?  pip install memprocfs",
                 bg=C["base"], fg=C["yellow"],
                 font=("Consolas", 8)).pack(anchor="w", padx=6, pady=(0, 4))

        # DMA HTTP server config (MemEdit server.py)
        self._tcp_frame = ttk.LabelFrame(p, text=" DMA / HTTP server (MemEdit server.py) ")
        self._tcp_frame.pack(fill="x", padx=8, pady=4)
        for label, var in [
            ("Host:",         self._var_tcp_host),
            ("Port:",         self._var_tcp_port),
            ("Process name:", self._var_tcp_proc),
            ("Token:",        self._var_tcp_token),
        ]:
            row = tk.Frame(self._tcp_frame, bg=C["base"])
            row.pack(fill="x", padx=6, pady=2)
            tk.Label(row, text=label, bg=C["base"], fg=C["subtext0"],
                     font=("Consolas", 8), anchor="w", width=14).pack(side="left")
            ttk.Entry(row, textvariable=var, font=("Consolas", 9),
                      show="*" if label == "Token:" else "").pack(
                      side="left", fill="x", expand=True)
        tk.Label(self._tcp_frame,
                 text="  python apps/MemEdit/server.py --device fpga --port 8765 --token ...",
                 bg=C["base"], fg=C["subtext0"],
                 font=("Consolas", 8)).pack(anchor="w", padx=6, pady=(0, 4))

        # Attach / Detach
        btn_row = tk.Frame(p, bg=C["mantle"])
        btn_row.pack(fill="x", padx=8, pady=4)
        ttk.Button(btn_row, text="Attach", style="Accent.TButton",
                   command=self._attach).pack(
                   side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(btn_row, text="Detach",
                   command=self._detach).pack(
                   side="left", fill="x", expand=True, padx=(2, 0))

        # Memory offsets
        of = ttk.LabelFrame(p, text=" Memory Offsets (hex) ")
        of.pack(fill="x", padx=8, pady=4)
        for label, var in [
            ("GObjects VA:",    self._var_gobjects),
            ("GNames VA:",      self._var_gnames),
            ("Name field off:", self._var_nameoff),
            ("Name str off:",   self._var_namestroff),
        ]:
            row = tk.Frame(of, bg=C["base"])
            row.pack(fill="x", padx=6, pady=2)
            tk.Label(row, text=label, bg=C["base"], fg=C["subtext0"],
                     font=("Consolas", 8), width=16, anchor="w").pack(side="left")
            ttk.Entry(row, textvariable=var, width=13,
                      font=("Consolas", 9)).pack(side="left")

        cb_row = tk.Frame(of, bg=C["base"])
        cb_row.pack(fill="x", padx=6, pady=(2, 4))
        ttk.Checkbutton(cb_row, text="64-bit process",
                        variable=self._var_64bit).pack(side="left")
        ttk.Button(of, text="Auto-detect name offset",
                   command=self._auto_detect).pack(fill="x", padx=6, pady=(0, 4))
        ttk.Button(of, text="Scan Signatures \u2192 update VAs",
                   command=self._scan_signatures).pack(fill="x", padx=6, pady=(0, 6))

        # Actions
        af = ttk.LabelFrame(p, text=" Actions ")
        af.pack(fill="x", padx=8, pady=4)
        for text, cmd in [
            ("Dump Names",        self._dump_names),
            ("Dump Objects",      self._dump_objects),
            ("Export Names...",   self._export_names),
            ("Export Objects...", self._export_objects),
            ("Generate SDK...",   self._generate_sdk),
        ]:
            ttk.Button(af, text=text, command=cmd).pack(fill="x", padx=6, pady=2)
        tk.Frame(af, bg=C["base"], height=4).pack()

        self._on_mode_change()

    def _on_mode_change(self) -> None:
        mode = self._var_mode.get()
        for frame, vis in [
            (self._native_frame, "native"),
            (self._vmm_frame,    "dma_vmm"),
            (self._tcp_frame,    "dma_tcp"),
        ]:
            if mode == vis:
                frame.pack(fill="x", padx=8, pady=4)
            else:
                frame.pack_forget()

    # ── content notebook ─────────────────────────────────────────────────

    def _build_content(self, parent: tk.Frame) -> None:
        self._nb = ttk.Notebook(parent)
        self._nb.pack(fill="both", expand=True, padx=4, pady=4)

        self._tab_names   = ttk.Frame(self._nb)
        self._tab_objects = ttk.Frame(self._nb)
        self._tab_bf      = ttk.Frame(self._nb)
        self._tab_sdk     = ttk.Frame(self._nb)
        self._tab_log     = ttk.Frame(self._nb)

        self._nb.add(self._tab_names,   text="  Names  ")
        self._nb.add(self._tab_objects, text="  Objects  ")
        self._nb.add(self._tab_bf,      text="  Brute Force  ")
        self._nb.add(self._tab_sdk,     text="  SDK Output  ")
        self._nb.add(self._tab_log,     text="  Log  ")

        self._build_names_tab()
        self._build_objects_tab()
        self._build_bruteforce_tab()
        self._build_sdk_tab()
        self._build_log_tab()

    # ── Names tab ────────────────────────────────────────────────────────

    def _build_names_tab(self) -> None:
        top = ttk.Frame(self._tab_names, padding=(6, 4, 6, 0))
        top.pack(fill="x")
        ttk.Button(top, text="Dump Names", command=self._dump_names).pack(side="left")
        tk.Label(top, text="  Filter: ", bg=C["base"], fg=C["subtext0"],
                 font=("Consolas", 9)).pack(side="left")
        self._name_filter = tk.StringVar()
        self._name_filter.trace_add("write", lambda *_: self._apply_name_filter())
        ttk.Entry(top, textvariable=self._name_filter, width=28).pack(side="left")
        self._name_count_lbl = tk.Label(top, text="0 names",
                                         bg=C["base"], fg=C["subtext0"],
                                         font=("Consolas", 9))
        self._name_count_lbl.pack(side="right")

        f = ttk.Frame(self._tab_names, padding=6)
        f.pack(fill="both", expand=True)
        self._names_tv = ttk.Treeview(f, columns=("idx", "name"), show="headings")
        self._names_tv.heading("idx",  text="Index")
        self._names_tv.heading("name", text="Name")
        self._names_tv.column("idx",  width=80,  anchor="e")
        self._names_tv.column("name", width=700)
        nsby = ttk.Scrollbar(f, orient="vertical",   command=self._names_tv.yview)
        nsbx = ttk.Scrollbar(f, orient="horizontal", command=self._names_tv.xview)
        self._names_tv.configure(yscrollcommand=nsby.set, xscrollcommand=nsbx.set)
        self._names_tv.grid(row=0, column=0, sticky="nsew")
        nsby.grid(row=0, column=1, sticky="ns")
        nsbx.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1); f.columnconfigure(0, weight=1)

    # ── Objects tab ──────────────────────────────────────────────────────

    def _build_objects_tab(self) -> None:
        top = ttk.Frame(self._tab_objects, padding=(6, 4, 6, 0))
        top.pack(fill="x")
        ttk.Button(top, text="Dump Objects", command=self._dump_objects).pack(side="left")
        tk.Label(top, text="  Filter: ", bg=C["base"], fg=C["subtext0"],
                 font=("Consolas", 9)).pack(side="left")
        self._obj_filter = tk.StringVar()
        self._obj_filter.trace_add("write", lambda *_: self._apply_obj_filter())
        ttk.Entry(top, textvariable=self._obj_filter, width=28).pack(side="left")
        self._obj_count_lbl = tk.Label(top, text="0 objects",
                                        bg=C["base"], fg=C["subtext0"],
                                        font=("Consolas", 9))
        self._obj_count_lbl.pack(side="right")

        f = ttk.Frame(self._tab_objects, padding=6)
        f.pack(fill="both", expand=True)
        cols = ("idx", "ptr", "ni", "name")
        self._objs_tv = ttk.Treeview(f, columns=cols, show="headings")
        self._objs_tv.heading("idx",  text="Index")
        self._objs_tv.heading("ptr",  text="Address")
        self._objs_tv.heading("ni",   text="NameIdx")
        self._objs_tv.heading("name", text="Name")
        self._objs_tv.column("idx",  width=70,  anchor="e")
        self._objs_tv.column("ptr",  width=130, anchor="e")
        self._objs_tv.column("ni",   width=80,  anchor="e")
        self._objs_tv.column("name", width=600)
        osby = ttk.Scrollbar(f, orient="vertical",   command=self._objs_tv.yview)
        osbx = ttk.Scrollbar(f, orient="horizontal", command=self._objs_tv.xview)
        self._objs_tv.configure(yscrollcommand=osby.set, xscrollcommand=osbx.set)
        self._objs_tv.grid(row=0, column=0, sticky="nsew")
        osby.grid(row=0, column=1, sticky="ns")
        osbx.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1); f.columnconfigure(0, weight=1)

        ctx = tk.Menu(self, tearoff=0,
                      bg=C["srf0"], fg=C["text"],
                      activebackground=C["blue"], activeforeground=C["base"])
        ctx.add_command(label="Copy address",
                        command=lambda: self._obj_copy_field("ptr"))
        ctx.add_command(label="Copy name",
                        command=lambda: self._obj_copy_field("name"))
        self._objs_tv.bind("<Button-3>",
            lambda e: (self._objs_tv.selection_set(
                        self._objs_tv.identify_row(e.y)),
                       ctx.tk_popup(e.x_root, e.y_root)))

    # ── Brute force tab ──────────────────────────────────────────────────

    def _build_bruteforce_tab(self) -> None:
        # ── Discovery controls ───────────────────────────────────────────
        top = ttk.LabelFrame(self._tab_bf, text=" Brute Force Discovery ")
        top.pack(fill="x", padx=10, pady=(8, 4))

        cfg = tk.Frame(top, bg=C["base"])
        cfg.pack(fill="x", padx=8, pady=(6, 2))
        for label, attr, default, w in [
            ("Module base:", "_var_modbase", "0x00400000", 14),
            ("Scan length:", "_var_scanlen", "0x02000000", 12),
        ]:
            tk.Label(cfg, text=label, bg=C["base"], fg=C["subtext0"],
                     font=("Consolas", 9)).pack(side="left")
            sv = tk.StringVar(value=default)
            setattr(self, attr, sv)
            ttk.Entry(cfg, textvariable=sv, width=w,
                      font=("Consolas", 9)).pack(side="left", padx=(2, 10))

        tk.Label(cfg, text="64-bit:", bg=C["base"], fg=C["subtext0"],
                 font=("Consolas", 9)).pack(side="left")
        ttk.Checkbutton(cfg, variable=self._var_64bit).pack(side="left", padx=(2, 0))

        btn_row = tk.Frame(top, bg=C["base"])
        btn_row.pack(fill="x", padx=8, pady=(4, 2))
        ttk.Button(btn_row, text="Full Discovery  (Patterns + TArray + Offsets)",
                   command=self._bf_discover).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="TArray Scan Only",
                   command=self._bf_tarrays_only).pack(side="left")

        # ── Progress bar ─────────────────────────────────────────────────
        prog_frame = tk.Frame(top, bg=C["base"])
        prog_frame.pack(fill="x", padx=8, pady=(4, 6))
        self._bf_progress_var = tk.DoubleVar(value=0.0)
        self._bf_progress_msg = tk.StringVar(value="Idle.")
        self._bf_prog_bar = ttk.Progressbar(
            prog_frame, variable=self._bf_progress_var,
            maximum=100.0, length=420, mode="determinate")
        self._bf_prog_bar.pack(side="left", fill="x", expand=True)
        tk.Label(prog_frame, textvariable=self._bf_progress_msg,
                 bg=C["base"], fg=C["subtext0"],
                 font=("Consolas", 8), anchor="w", width=34).pack(side="left", padx=(6, 0))

        # ── Results table ────────────────────────────────────────────────
        res = ttk.LabelFrame(self._tab_bf, text=" Discovery Results  (sorted by confidence) ")
        res.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("conf", "gobj_va", "gnam_va", "noff", "nsoff", "pattern")
        self._bf_tv = ttk.Treeview(res, columns=cols, show="headings")
        for col, cw, txt, anch in [
            ("conf",    80,  "Confidence", "center"),
            ("gobj_va", 130, "GObjects VA", "e"),
            ("gnam_va", 130, "GNames VA",  "e"),
            ("noff",    80,  "NameOff",    "e"),
            ("nsoff",   80,  "StrOff",     "e"),
            ("pattern", 340, "Pattern / Source", "w"),
        ]:
            self._bf_tv.heading(col, text=txt)
            self._bf_tv.column(col, width=cw, anchor=anch)
        bf_sb = ttk.Scrollbar(res, orient="vertical", command=self._bf_tv.yview)
        self._bf_tv.configure(yscrollcommand=bf_sb.set)
        self._bf_tv.pack(side="left", fill="both", expand=True)
        bf_sb.pack(side="right", fill="y")
        self._bf_tv.tag_configure("good",   background=C["srf0"], foreground=C["green"])
        self._bf_tv.tag_configure("medium", background=C["srf0"], foreground=C["yellow"])
        self._bf_tv.tag_configure("low",    background=C["srf0"], foreground=C["subtext0"])

        # Also keep the old TArray-only candidates section for quick scan results
        ta_lf = ttk.LabelFrame(self._tab_bf, text=" TArray Candidates ")
        ta_lf.pack(fill="x", padx=10, pady=(0, 4))
        ta_cols = ("va", "offset", "data_ptr", "count", "max", "note")
        self._ta_tv = ttk.Treeview(ta_lf, columns=ta_cols, show="headings", height=5)
        for col, cw, txt, anch in [
            ("va",       130, "Virtual Address", "e"),
            ("offset",   110, "Module Offset",   "e"),
            ("data_ptr", 130, "Data Ptr",        "e"),
            ("count",     80, "Count",           "e"),
            ("max",       80, "Max",             "e"),
            ("note",     280, "Notes",           "w"),
        ]:
            self._ta_tv.heading(col, text=txt)
            self._ta_tv.column(col, width=cw, anchor=anch)
        ta_sb = ttk.Scrollbar(ta_lf, orient="vertical", command=self._ta_tv.yview)
        self._ta_tv.configure(yscrollcommand=ta_sb.set)
        self._ta_tv.pack(side="left", fill="both", expand=True)
        ta_sb.pack(side="right", fill="y")

        # ── Action buttons ───────────────────────────────────────────────
        act_row = tk.Frame(self._tab_bf, bg=C["base"])
        act_row.pack(fill="x", padx=10, pady=(2, 8))
        ttk.Button(act_row, text="Apply Selected to Sidebar",
                   command=self._bf_apply).pack(side="left", padx=(0, 6))
        ttk.Button(act_row, text="Use TArray as GObjects",
                   command=lambda: self._bf_use_ta("gobjects")).pack(side="left", padx=(0, 4))
        ttk.Button(act_row, text="Use TArray as GNames",
                   command=lambda: self._bf_use_ta("gnames")).pack(side="left", padx=(0, 12))
        ttk.Button(act_row, text="Dump Names + Objects",
                   command=self._bf_dump_all).pack(side="left", padx=(0, 6))
        ttk.Button(act_row, text="Export Game Pack…",
                   command=self._export_pack).pack(side="left")

    # ── SDK tab ──────────────────────────────────────────────────────────

    def _build_sdk_tab(self) -> None:
        top = ttk.Frame(self._tab_sdk, padding=(6, 4, 6, 0))
        top.pack(fill="x")
        for text, cmd in [
            ("Generate SDK", self._generate_sdk),
            ("Copy All",     self._sdk_copy),
            ("Save...",      self._sdk_save),
        ]:
            ttk.Button(top, text=text, command=cmd).pack(side="left", padx=2)

        tk.Label(top, text="    Language:",
                 bg=C["base"], fg=C["subtext0"],
                 font=("Consolas", 9)).pack(side="left")
        for val, lbl in [("cpp", "C++"), ("python", "Python")]:
            ttk.Radiobutton(top, text=lbl, variable=self._var_sdk_lang,
                            value=val).pack(side="left", padx=2)

        tk.Label(top, text="   Target:",
                 bg=C["base"], fg=C["subtext0"],
                 font=("Consolas", 9)).pack(side="left")
        for val, lbl in [("native", "Native"), ("dma", "DMA"), ("both", "Both")]:
            ttk.Radiobutton(top, text=lbl, variable=self._var_sdk_target,
                            value=val).pack(side="left", padx=2)

        f = ttk.Frame(self._tab_sdk, padding=6)
        f.pack(fill="both", expand=True)
        self._sdk_text = tk.Text(
            f, bg=C["mantle"], fg=C["text"],
            insertbackground=C["text"],
            font=("Consolas", 9), wrap="none",
            borderwidth=0, highlightthickness=0)
        sdk_sby = ttk.Scrollbar(f, orient="vertical",   command=self._sdk_text.yview)
        sdk_sbx = ttk.Scrollbar(f, orient="horizontal", command=self._sdk_text.xview)
        self._sdk_text.configure(yscrollcommand=sdk_sby.set, xscrollcommand=sdk_sbx.set)
        self._sdk_text.grid(row=0, column=0, sticky="nsew")
        sdk_sby.grid(row=0, column=1, sticky="ns")
        sdk_sbx.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1); f.columnconfigure(0, weight=1)
        self._sdk_text.insert("end",
            "// UE3 SDK Generator\n"
            "// Dump GNames and GObjects first, then click Generate SDK.\n"
            "// Select Language (C++/Python) and Target (Native/DMA/Both).\n")

    # ── Log tab ──────────────────────────────────────────────────────────

    def _build_log_tab(self) -> None:
        f = ttk.Frame(self._tab_log, padding=6)
        f.pack(fill="both", expand=True)
        self._log_text = tk.Text(
            f, bg=C["mantle"], fg=C["text"],
            insertbackground=C["text"],
            font=("Consolas", 9), wrap="none",
            state="disabled", borderwidth=0, highlightthickness=0)
        log_sb = ttk.Scrollbar(f, orient="vertical", command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_sb.set)
        self._log_text.pack(side="left", fill="both", expand=True)
        log_sb.pack(side="right", fill="y")
        btn_row = tk.Frame(self._tab_log, bg=C["base"])
        btn_row.pack(fill="x", padx=6, pady=4)
        ttk.Button(btn_row, text="Clear", command=self._clear_log).pack(side="left")

    # ═══════════════════════════════════════════════════════════════════════
    # Profile
    # ═══════════════════════════════════════════════════════════════════════

    def _load_profile(self, key: str) -> None:
        prof = GAME_PROFILES.get(key)
        if not prof:
            return
        if key == "CUSTOM":
            # Custom profile: clear VAs, keep default offsets, don't overwrite process name
            self._var_gobjects.set("0x00000000")
            self._var_gnames.set("0x00000000")
            self._var_nameoff.set("0x2C")
            self._var_namestroff.set("0x10")
            self._var_64bit.set(False)
            self._set_status(
                "Custom profile — select a process from the list, then run Brute Force discovery.")
            self._log("[*] Profile: CUSTOM — brute-force mode")
            self._update_ue_badge("UE3")
            self._nb.select(self._tab_bf)
            return
        gobj = prof.get("gobjects_va", 0)
        gnam = prof.get("gnames_va",   0)
        self._var_gobjects.set(  f"0x{gobj:08X}" if gobj else "0x00000000")
        self._var_gnames.set(    f"0x{gnam:08X}" if gnam else "0x00000000")
        self._var_nameoff.set(   f"0x{prof.get('name_field_off', 0x2C):02X}")
        self._var_namestroff.set(f"0x{prof.get('name_str_off',   0x10):02X}")
        self._var_64bit.set(prof.get("is64", False))
        proc = prof.get("process", "")
        self._var_vmm_proc.set(proc)
        self._var_tcp_proc.set(proc)
        self._set_status(f"Profile: {prof['name']}  ({prof.get('notes','')})")
        self._log(f"[*] Profile loaded: {key} — {prof['name']}")
        self._update_ue_badge(prof.get("ue_version", "UE3"))

    _UE_BADGE_COLORS = {
        "UE1": ("#1e1e2e", "#a6e3a1"),  # green
        "UE2": ("#1e1e2e", "#a6da95"),  # green-2
        "UE3": ("#1e1e2e", "#89b4fa"),  # blue
        "UE4": ("#1e1e2e", "#cba6f7"),  # mauve/purple
    }

    def _update_ue_badge(self, ue_ver: str) -> None:
        fg, bg = self._UE_BADGE_COLORS.get(ue_ver, ("#1e1e2e", "#6c7086"))
        self._ue_badge.configure(text=ue_ver, fg=fg, bg=bg)


    # ═══════════════════════════════════════════════════════════════════════
    # Connection
    # ═══════════════════════════════════════════════════════════════════════

    def _refresh_procs(self) -> None:
        self._procs = list_procs()
        self._filter_procs()

    def _filter_procs(self) -> None:
        flt = self._var_proc_flt.get().lower()
        self._proc_lb.delete(0, "end")
        for pid, name in self._procs:
            if not flt or flt in name.lower() or flt in str(pid):
                self._proc_lb.insert("end", f"[{pid:5d}] {name}")

    def _on_proc_select(self, _event=None) -> None:
        """When a process is clicked in the list, fill the process-name fields."""
        sel = self._proc_lb.curselection()
        if not sel:
            return
        line   = self._proc_lb.get(sel[0])        # "[  PID] name.exe"
        parts  = line.split("]", 1)
        if len(parts) < 2:
            return
        name = parts[1].strip()
        self._var_vmm_proc.set(name)
        self._var_tcp_proc.set(name)

    def _selected_pid(self) -> Optional[int]:
        sel = self._proc_lb.curselection()
        if not sel:
            return None
        try:
            return int(self._proc_lb.get(sel[0])[1:6].strip())
        except ValueError:
            return None

    def _attach(self) -> None:
        if self._backend:
            self._detach()
        mode = self._var_mode.get()
        try:
            if mode == "native":
                pid = self._selected_pid()
                if not pid:
                    messagebox.showwarning("No selection",
                        "Select a process from the list first.")
                    return
                self._backend = NativeBackend(pid)
            elif mode == "dma_vmm":
                self._backend = VmmBackend(
                    device       = self._var_vmm_device.get().strip(),
                    process_name = self._var_vmm_proc.get().strip())
            elif mode == "dma_tcp":
                port = int(self._var_tcp_port.get().strip())
                self._backend = SocketDMABackend(
                    host         = self._var_tcp_host.get().strip(),
                    port         = port,
                    process_name = self._var_tcp_proc.get().strip(),
                    token        = self._var_tcp_token.get().strip())
        except Exception as exc:
            msg = str(exc)
            self._set_status(f"Attach failed: {msg.splitlines()[0]}")
            self._log(f"[!] Attach failed: {msg}")
            # Show a dialog only for unexpected errors; soft-import failures
            # (vmmpy / socket) are already described in the log.
            if "not installed" not in msg.lower() and "connection" not in msg.lower():
                messagebox.showerror("Attach failed", msg)
            return

        self._reader = self._make_reader()
        desc = self._backend.description
        self._conn_dot.config(text=f"[+] {desc}", fg=C["green"])
        self._set_status(f"Attached — {desc}")
        self._log(f"[+] Attached — {desc}")

    def _detach(self) -> None:
        if self._backend:
            self._backend.close()
        self._backend = None
        self._reader  = None
        self._conn_dot.config(text="[x] Detached", fg=C["red"])
        self._set_status("Detached")
        self._log("[+] Detached")

    def _make_reader(self) -> UE3Reader:
        def _h(s: str) -> int:
            s = s.strip()
            return int(s, 16) if s.lower().startswith("0x") else int(s)

        prof = GAME_PROFILES.get(self._var_profile.get(), {})
        enc  = prof.get("name_encoding", "ascii")

        return UE3Reader(
            backend        = self._backend,
            gobjects_va    = _h(self._var_gobjects.get()),
            gnames_va      = _h(self._var_gnames.get()),
            name_field_off = _h(self._var_nameoff.get()),
            name_str_off   = _h(self._var_namestroff.get()),
            name_encoding  = enc,
            is64           = self._var_64bit.get(),
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Dump
    # ═══════════════════════════════════════════════════════════════════════

    def _dump_names(self) -> None:
        if not self._check_attached():
            return
        self._reader = self._make_reader()
        self._set_status("Dumping GNames…")
        self._log("[*] Dumping GNames — streaming live…")
        # Clear table and switch to Names tab immediately so user sees live rows
        self._names_tv.delete(*self._names_tv.get_children())
        self._name_count_lbl.config(text="0 names")
        self._nb.select(self._tab_names)

        _buf: list = []
        _total = [0]
        _BATCH = 25

        def _push(batch: list, total: int) -> None:
            for idx, name in batch:
                self._names_tv.insert("", "end", values=(idx, name))
            ch = self._names_tv.get_children()
            if ch:
                self._names_tv.see(ch[-1])
            self._name_count_lbl.config(text=f"{total:,} names")
            ts = time.strftime("%H:%M:%S")
            self._log_text.config(state="normal")
            self._log_text.insert("end",
                "".join(f"[{ts}]  Name[{idx:05d}]  {name}\n"
                        for idx, name in batch))
            self._log_text.see("end")
            self._log_text.config(state="disabled")

        def _work() -> None:
            def _progress(i: int, n: int) -> None:
                self.after(0, lambda i=i, n=n:
                           self._set_status(f"GNames: {i:,} / {n:,}"))

            def _item(idx: int, name: str) -> None:
                _buf.append((idx, name))
                _total[0] += 1
                if len(_buf) >= _BATCH:
                    snap = _buf[:]
                    _buf.clear()
                    t = _total[0]
                    self.after(0, lambda b=snap, c=t: _push(b, c))

            names = self._reader.dump_names(cb=_progress, item_cb=_item)
            # flush any remaining partial batch
            if _buf:
                snap = _buf[:]
                t = _total[0]
                self.after(0, lambda b=snap, c=t: _push(b, c))
            self.after(0, lambda: self._on_names_done(names))

        threading.Thread(target=_work, daemon=True).start()

    def _on_names_done(self, names: Dict[int, str]) -> None:
        self._names = names
        self._name_count_lbl.config(text=f"{len(names):,} names")
        self._set_status(f"GNames: {len(names):,} entries")
        self._log(f"[+] GNames complete \u2014 {len(names):,} names")
        self._nb.select(self._tab_names)

    def _repopulate_names(self) -> None:
        flt = self._name_filter.get().lower()
        self._names_tv.delete(*self._names_tv.get_children())
        shown = 0
        for idx, name in sorted(self._names.items()):
            if not flt or flt in name.lower() or flt in str(idx):
                self._names_tv.insert("", "end", values=(idx, name))
                shown += 1
        self._name_count_lbl.config(
            text=f"{shown:,} / {len(self._names):,} names")

    def _apply_name_filter(self) -> None:
        if self._names:
            self._repopulate_names()

    def _dump_objects(self) -> None:
        if not self._check_attached():
            return
        if not self._names:
            if not messagebox.askyesno("GNames not loaded",
                    "GNames not loaded yet — names will show as '?<index>'.\n"
                    "Continue anyway?"):
                return
        self._reader = self._make_reader()
        self._set_status("Dumping GObjects…")
        self._log("[*] Dumping GObjects — streaming live…")
        # Clear table and switch to Objects tab so user sees live rows
        self._objs_tv.delete(*self._objs_tv.get_children())
        self._obj_count_lbl.config(text="0 objects")
        self._nb.select(self._tab_objects)

        _buf: list = []
        _total = [0]
        _BATCH = 25

        def _push(batch: list, total: int) -> None:
            for o in batch:
                self._objs_tv.insert("", "end", values=(
                    o["index"], f"0x{o['ptr']:08X}", o["name_index"], o["name"]))
            ch = self._objs_tv.get_children()
            if ch:
                self._objs_tv.see(ch[-1])
            self._obj_count_lbl.config(text=f"{total:,} objects")
            ts = time.strftime("%H:%M:%S")
            self._log_text.config(state="normal")
            self._log_text.insert("end",
                "".join(f"[{ts}]  Object[{o['index']:05d}]  0x{o['ptr']:08X}  {o['name']}\n"
                        for o in batch))
            self._log_text.see("end")
            self._log_text.config(state="disabled")

        def _work() -> None:
            def _progress(i: int, n: int) -> None:
                self.after(0, lambda i=i, n=n:
                           self._set_status(f"GObjects: {i:,} / {n:,}"))

            def _item(obj: dict) -> None:
                _buf.append(obj)
                _total[0] += 1
                if len(_buf) >= _BATCH:
                    snap = _buf[:]
                    _buf.clear()
                    t = _total[0]
                    self.after(0, lambda b=snap, c=t: _push(b, c))

            objs = self._reader.dump_objects(self._names, cb=_progress, item_cb=_item)
            # flush any remaining partial batch
            if _buf:
                snap = _buf[:]
                t = _total[0]
                self.after(0, lambda b=snap, c=t: _push(b, c))
            self.after(0, lambda: self._on_objects_done(objs))

        threading.Thread(target=_work, daemon=True).start()

    def _on_objects_done(self, objs: List[Dict]) -> None:
        self._objects = objs
        self._obj_count_lbl.config(text=f"{len(objs):,} objects")
        self._set_status(f"GObjects: {len(objs):,} objects")
        self._log(f"[+] GObjects complete \u2014 {len(objs):,} objects")
        self._nb.select(self._tab_objects)

    def _repopulate_objects(self) -> None:
        flt = self._obj_filter.get().lower()
        self._objs_tv.delete(*self._objs_tv.get_children())
        shown = 0
        for o in self._objects:
            name = o["name"]
            if not flt or flt in name.lower() or f"{o['ptr']:#010x}".__contains__(flt):
                self._objs_tv.insert("", "end", values=(
                    o["index"], f"0x{o['ptr']:08X}", o["name_index"], name))
                shown += 1
        self._obj_count_lbl.config(
            text=f"{shown:,} / {len(self._objects):,} objects")

    def _apply_obj_filter(self) -> None:
        if self._objects:
            self._repopulate_objects()

    def _obj_copy_field(self, col: str) -> None:
        sel = self._objs_tv.selection()
        if not sel:
            return
        vals = self._objs_tv.item(sel[0], "values")
        field_map = {"ptr": 1, "name": 3}
        text = vals[field_map.get(col, 3)]
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(f"Copied: {text}")

    # ═══════════════════════════════════════════════════════════════════════
    # Export
    # ═══════════════════════════════════════════════════════════════════════

    def _export_names(self) -> None:
        if not self._names:
            messagebox.showinfo("Nothing to export", "Dump GNames first.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile="GNames.txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")], title="Export GNames")
        if not dest:
            return
        with open(dest, "w", encoding="utf-8") as fh:
            for idx, name in sorted(self._names.items()):
                fh.write(f"Name[{idx:06d}] {name}\n")
        self._set_status(f"GNames saved → {dest}")
        self._log(f"[+] GNames exported: {dest}")

    def _export_objects(self) -> None:
        if not self._objects:
            messagebox.showinfo("Nothing to export", "Dump GObjects first.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile="GObjects.txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")], title="Export GObjects")
        if not dest:
            return
        with open(dest, "w", encoding="utf-8") as fh:
            for o in self._objects:
                fh.write(
                    f"Object[{o['index']:06d}]  {o['ptr']:#010x}"
                    f"  {o['name']}\n")
        self._set_status(f"GObjects saved → {dest}")
        self._log(f"[+] GObjects exported: {dest}")

    # ═══════════════════════════════════════════════════════════════════════
    # Auto-detect
    # ═══════════════════════════════════════════════════════════════════════

    def _auto_detect(self) -> None:
        if not self._check_attached():
            return
        if not self._names:
            messagebox.showinfo("Dump names first",
                "Load GNames first so the heuristic has indices to match against.")
            return
        self._set_status("Auto-detecting NameIndex field offset…")

        def _work() -> None:
            reader = self._make_reader()
            off    = reader.detect_name_offset(self._names)
            self.after(0, lambda o=off: self._on_autodetect(o))

        threading.Thread(target=_work, daemon=True).start()

    def _on_autodetect(self, off: Optional[int]) -> None:
        if off is None:
            messagebox.showinfo("Auto-detect",
                "Could not determine name field offset.")
            self._set_status("Auto-detect: no result")
        else:
            self._var_nameoff.set(f"0x{off:02X}")
            self._set_status(f"Auto-detect: NameIndex offset = {off:#04x}")
            self._log(f"[+] Auto-detect: NameIndex offset = {off:#04x}")
            messagebox.showinfo("Auto-detect",
                f"Detected NameIndex field offset: {off:#04x}\n"
                "Field updated.")

    # ═══════════════════════════════════════════════════════════════════════
    # Signature scan — find current GObjects/GNames VAs via byte patterns
    # ═══════════════════════════════════════════════════════════════════════

    def _scan_signatures(self) -> None:
        """Scan memory using the profile's byte-pattern signatures to locate
        the current GObjects/GNames VAs (works even when static VAs are stale).
        """
        if not self._check_attached():
            return
        key  = self._var_profile.get()
        prof = GAME_PROFILES.get(key, {})
        gobj_pat  = prof.get("gobj_pattern")
        gobj_mask = prof.get("gobj_mask", "")
        gobj_off  = prof.get("gobj_off",  0)
        gnam_pat  = prof.get("gnam_pattern")
        gnam_mask = prof.get("gnam_mask", "")
        gnam_off  = prof.get("gnam_off",  0)

        if not gobj_pat and not gnam_pat:
            messagebox.showinfo(
                "No signatures",
                f"Profile '{key}' has no byte-pattern signatures.\n"
                "Use Brute Force Discovery to scan for unknown VAs.")
            return

        # Use scan range from BF tab if already set, otherwise use defaults
        try:
            base = int(getattr(self, "_var_modbase", None).get(), 16)  # type: ignore[union-attr]
        except Exception:
            base = 0x00400000
        try:
            size = int(getattr(self, "_var_scanlen", None).get(), 16)  # type: ignore[union-attr]
        except Exception:
            size = 0x02000000

        is64 = self._var_64bit.get()
        self._set_status(f"Sig scan: searching 0x{base:08X}+0x{size:08X}…")
        self._log(
            f"[*] Sig scan: profile={key}  base=0x{base:08X}  "
            f"len=0x{size:08X}  64bit={is64}")

        def _work() -> None:
            scanner = PatternScanner(self._backend)
            gobj_va = gnam_va = None
            if gobj_pat:
                self.after(0, lambda: self._set_status("Sig scan: scanning for GObjects…"))
                gobj_va = scanner.scan(base, size, gobj_pat, gobj_mask, gobj_off, is64)
            if gnam_pat:
                self.after(0, lambda: self._set_status("Sig scan: scanning for GNames…"))
                gnam_va = scanner.scan(base, size, gnam_pat, gnam_mask, gnam_off, is64)
            self.after(0, lambda: self._on_sigscan_done(gobj_va, gnam_va))

        threading.Thread(target=_work, daemon=True).start()

    def _on_sigscan_done(self, gobj_va: Optional[int],
                          gnam_va: Optional[int]) -> None:
        found: List[str] = []
        if gobj_va:
            self._var_gobjects.set(f"0x{gobj_va:08X}")
            found.append(f"GObjects=0x{gobj_va:08X}")
            self._log(f"[+] Sig scan → GObjects VA = 0x{gobj_va:08X}")
        else:
            self._log("[!] Sig scan → GObjects: signature not found")
        if gnam_va:
            self._var_gnames.set(f"0x{gnam_va:08X}")
            found.append(f"GNames=0x{gnam_va:08X}")
            self._log(f"[+] Sig scan → GNames VA = 0x{gnam_va:08X}")
        else:
            self._log("[!] Sig scan → GNames: signature not found")
        if found:
            self._set_status("Sig scan done: " + "  ".join(found))
            self._log("[+] VA fields updated — ready to Dump Names / Dump Objects")
        else:
            self._set_status(
                "Sig scan: nothing found — verify scan range or try Brute Force Discovery")

    # ═══════════════════════════════════════════════════════════════════════
    # Brute force / discovery actions
    # ═══════════════════════════════════════════════════════════════════════

    def _bf_discover(self) -> None:
        """Full discovery: patterns + TArray scan + offset brute force."""
        if not self._check_attached():
            return
        try:
            base = int(self._var_modbase.get(), 16)
            size = int(self._var_scanlen.get(),  16)
        except ValueError:
            messagebox.showerror("Parse error",
                "Module base and scan length must be hex (e.g. 0x00400000).")
            return
        is64 = self._var_64bit.get()
        self._bf_progress_var.set(0.0)
        self._bf_progress_msg.set("Starting full discovery…")
        # Clear results table so live hits appear fresh
        self._bf_tv.delete(*self._bf_tv.get_children())

        def _work() -> None:
            bf = BruteForcer(self._backend, base, size, is64)

            def _cb(msg: str, fraction: float) -> None:
                self.after(0, lambda m=msg, f=fraction: (
                    self._bf_progress_msg.set(m),
                    self._bf_progress_var.set(round(f * 100, 1)),
                ))

            def _hit_cb(result: dict) -> None:
                """Called for each scored result as soon as it is ready."""
                self.after(0, lambda r=result: self._bf_insert_result_live(r))

            def _raw_hit_cb(hit: dict) -> None:
                """Called for each raw pattern match before scoring."""
                msg = (f"[scan] Pattern match: "
                       f"GObj=0x{hit['gobj_va']:08X}  "
                       f"GNames=0x{hit['gnam_va']:08X}  "
                       f"[{hit['pattern']}]")
                self.after(0, lambda m=msg: self._log(m))

            results = bf.full_discover(_cb, hit_cb=_hit_cb, raw_hit_cb=_raw_hit_cb)
            self.after(0, lambda r=results: self._on_bf_discover_done(r))

        threading.Thread(target=_work, daemon=True).start()

    def _bf_tarrays_only(self) -> None:
        """Quick TArray scan only (no pattern matching, no offset brute force)."""
        if not self._check_attached():
            return
        try:
            base = int(self._var_modbase.get(), 16)
            size = int(self._var_scanlen.get(),  16)
        except ValueError:
            messagebox.showerror("Parse error",
                "Module base and scan length must be hex (e.g. 0x00400000).")
            return
        self._bf_progress_var.set(0.0)
        self._bf_progress_msg.set("TArray scan…")

        def _work() -> None:
            reader = self._make_reader()

            def _inner_cb(done: int, total: int) -> None:
                pct = done / max(total, 1) * 100
                self.after(0, lambda p=pct, d=done, t=total: (
                    self._bf_progress_msg.set(f"TArray scan {d/max(t,1)*100:.0f}%"),
                    self._bf_progress_var.set(round(p, 1)),
                ))

            results = reader.scan_tarrays(base, size, _inner_cb)
            self.after(0, lambda r=results: self._on_ta_done(r))

        threading.Thread(target=_work, daemon=True).start()

    def _on_ta_done(self, results: List[Dict]) -> None:
        """Populate the TArray candidates table."""
        self._ta_tv.delete(*self._ta_tv.get_children())
        for r in results:
            self._ta_tv.insert("", "end", values=(
                f"0x{r['va']:010X}",
                f"0x{r['offset']:08X}",
                f"0x{r['data_ptr']:08X}",
                str(r["count"]),
                str(r["max"]),
                r["note"],
            ))
        self._bf_progress_msg.set(f"TArray scan complete — {len(results)} candidates.")
        self._bf_progress_var.set(100.0)
        self._set_status(f"TArray scan: {len(results)} candidates.")
        self._log(f"[+] TArray scan: {len(results)} candidates")
        self._nb.select(self._tab_bf)

    def _on_bf_discover_done(self, results: List[Dict]) -> None:
        """Finalize: re-sort and re-populate the results table by confidence."""
        # Re-populate sorted (live inserts were in discovery order)
        self._bf_tv.delete(*self._bf_tv.get_children())
        for r in results:
            conf = r["confidence"]
            tag  = "good" if conf >= 70 else ("medium" if conf >= 40 else "low")
            self._bf_tv.insert("", "end", tags=(tag,), values=(
                f"{conf}%",
                f"0x{r['gobj_va']:08X}",
                f"0x{r['gnam_va']:08X}",
                f"0x{r['name_field_off']:02X}",
                f"0x{r['name_str_off']:02X}",
                r["pattern"],
            ))
        if results:
            self._bf_best_result = results[0]
            self._bf_tv.selection_set(self._bf_tv.get_children()[0])
        self._bf_progress_msg.set(f"Done — {len(results)} result(s) found.")
        self._bf_progress_var.set(100.0)
        self._set_status(f"Discovery: {len(results)} candidate(s) found.")
        self._log(f"[+] Discovery complete: {len(results)} result(s)")
        self._nb.select(self._tab_bf)

    def _bf_insert_result_live(self, r: dict) -> None:
        """Insert one scored result into the BF table as it arrives."""
        conf = r["confidence"]
        tag  = "good" if conf >= 70 else ("medium" if conf >= 40 else "low")
        self._bf_tv.insert("", "end", tags=(tag,), values=(
            f"{conf}%",
            f"0x{r['gobj_va']:08X}",
            f"0x{r['gnam_va']:08X}",
            f"0x{r['name_field_off']:02X}",
            f"0x{r['name_str_off']:02X}",
            r["pattern"],
        ))
        self._log(
            f"[+] Hit  conf={conf}%  "
            f"GObj=0x{r['gobj_va']:08X}  GNames=0x{r['gnam_va']:08X}  "
            f"NameOff=0x{r['name_field_off']:02X}  StrOff=0x{r['name_str_off']:02X}  "
            f"pattern={r['pattern']}")

    def _bf_apply(self) -> None:
        """Apply the selected discovery result row to the sidebar fields."""
        sel = self._bf_tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a discovery result row first.")
            return
        vals = self._bf_tv.item(sel[0], "values")
        # vals: (conf%, gobj_va, gnam_va, noff, nsoff, pattern)
        self._var_gobjects.set(vals[1])
        self._var_gnames.set(vals[2])
        self._var_nameoff.set("0x" + vals[3].lstrip("0x"))
        self._var_namestroff.set("0x" + vals[4].lstrip("0x"))
        self._set_status(
            f"Applied: GObjects={vals[1]}  GNames={vals[2]}  "
            f"NameOff={vals[3]}  StrOff={vals[4]}")
        self._log(f"[+] Applied discovery result: {vals[5]}  conf={vals[0]}")

    def _bf_use_ta(self, which: str) -> None:
        """Apply selected TArray candidate as GObjects or GNames VA."""
        sel = self._ta_tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a TArray candidate row first.")
            return
        vals   = self._ta_tv.item(sel[0], "values")
        va_str = vals[0]   # already formatted as 0xADDR
        if which == "gobjects":
            self._var_gobjects.set(va_str)
            self._set_status(f"GObjects VA → {va_str}")
        else:
            self._var_gnames.set(va_str)
            self._set_status(f"GNames VA → {va_str}")
        self._log(f"[+] {'GObjects' if which == 'gobjects' else 'GNames'} VA = {va_str}")

    def _bf_dump_all(self) -> None:
        """Apply selected result then dump GNames and GObjects."""
        self._bf_apply()
        # _dump_names() runs in its own thread and chains to _dump_objects() on completion
        self._dump_names()

    def _export_pack(self) -> None:
        """Export a game pack folder: game_info.json, names_dump.txt, objects_dump.txt."""
        folder = filedialog.askdirectory(title="Select output folder for game pack")
        if not folder:
            return
        proc = (
            self._var_vmm_proc.get().strip()
            or self._var_tcp_proc.get().strip()
            or "unknown"
        )
        ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_proc = (proc.replace(".exe", "")
                        .replace("-",    "_")
                        .replace(" ",    "_"))
        pack_dir = pathlib.Path(folder) / f"{safe_proc}_{ts}"
        pack_dir.mkdir(parents=True, exist_ok=True)

        info: Dict = {
            "profile":          self._var_profile.get(),
            "process":          proc,
            "gobjects_va":      self._var_gobjects.get(),
            "gnames_va":        self._var_gnames.get(),
            "name_field_off":   self._var_nameoff.get(),
            "name_str_off":     self._var_namestroff.get(),
            "is64":             self._var_64bit.get(),
            "pattern_used":     (self._bf_best_result.get("pattern", "")
                                 if self._bf_best_result else ""),
            "confidence":       (self._bf_best_result.get("confidence", 0)
                                 if self._bf_best_result else 0),
            "export_timestamp": ts,
        }
        (pack_dir / "game_info.json").write_text(
            json.dumps(info, indent=2), encoding="utf-8")

        if self._names:
            lines = [f"Name[{i:06d}]  {n}"
                     for i, n in sorted(self._names.items())]
            (pack_dir / "names_dump.txt").write_text(
                "\n".join(lines), encoding="utf-8")

        if self._objects:
            lines = [f"Object[{o['index']:06d}]  0x{o['ptr']:08X}  {o['name']}"
                     for o in self._objects]
            (pack_dir / "objects_dump.txt").write_text(
                "\n".join(lines), encoding="utf-8")

        self._log(f"[+] Game pack exported → {pack_dir}")
        messagebox.showinfo("Export complete", f"Pack saved to:\n{pack_dir}")



    def _generate_sdk(self) -> None:
        if not self._names or not self._objects:
            messagebox.showinfo("Nothing to generate",
                "Dump GNames and GObjects first.")
            return

        cfg = {
            "sdk_lang":   self._var_sdk_lang.get(),
            "sdk_target": self._var_sdk_target.get(),
            "gobj_va":    self._var_gobjects.get().strip(),
            "gnam_va":    self._var_gnames.get().strip(),
            "name_off":   self._var_nameoff.get().strip(),
            "namestr_off":self._var_namestroff.get().strip(),
            "is64":       self._var_64bit.get(),
            "source_desc":self._backend.description if self._backend else "offline",
        }

        content = generate_sdk(self._names, self._objects, cfg)

        self._sdk_text.config(state="normal")
        self._sdk_text.delete("1.0", "end")
        self._sdk_text.insert("end", content)
        self._sdk_text.config(state="disabled")

        lines = content.count("\n")
        self._set_status(
            f"SDK generated (lang={cfg['sdk_lang']} target={cfg['sdk_target']}) "
            f"— {lines:,} lines")
        self._log(
            f"[+] SDK: lang={cfg['sdk_lang']}  target={cfg['sdk_target']}  "
            f"lines={lines}")
        self._nb.select(self._tab_sdk)

    def _sdk_copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._sdk_text.get("1.0", "end"))
        self._set_status("SDK copied to clipboard")

    def _sdk_save(self) -> None:
        lang = self._var_sdk_lang.get()
        ext  = ".py" if lang == "python" else ".h"
        dest = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=f"UE3SDK{ext}",
            filetypes=[
                ("Python", "*.py") if lang == "python" else ("C++ Header", "*.h *.hpp"),
                ("All", "*.*"),
            ],
            title="Save SDK")
        if not dest:
            return
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(self._sdk_text.get("1.0", "end"))
        self._set_status(f"SDK saved → {dest}")
        self._log(f"[+] SDK saved: {dest}")

    # ═══════════════════════════════════════════════════════════════════════
    # Log / status helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self._log_text.config(state="normal")
        self._log_text.insert("end", f"[{ts}] {msg}\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _clear_log(self) -> None:
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def _check_attached(self) -> bool:
        if not self._backend:
            messagebox.showwarning("Not attached",
                "Attach to a process first (Native or DMA).")
            return False
        return True
