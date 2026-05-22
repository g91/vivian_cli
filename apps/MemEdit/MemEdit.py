"""
MemEdit — Cheat Engine / T-Search style DMA memory editor GUI.

Attaches to any Windows process via PCILeech FPGA DMA (or native/file mode)
and provides:
  - Process browser with filter
  - Memory scanning: exact, range, unknown, changed/unchanged/increased/decreased
  - String and Array-of-Bytes (AoB) pattern search
  - Live-editable results table
  - Address list with freeze / thaw / label
  - Module and memory region browsers
  - Pointer chain resolver

Requirements:
    pip install memprocfs
    MemProcFS native binaries: https://github.com/ufrisk/MemProcFS/releases

Launch:
    python apps/MemEdit/MemEdit.py     (from vivian_cli/ root)
    -- or --
    double-click  apps/MemEdit/launch.bat
"""
from __future__ import annotations

import sys
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# ── path bootstrap ─────────────────────────────────────────────────────────────
_HERE     = Path(__file__).resolve().parent
_TOOL_DIR = _HERE.parent.parent / "tools" / "DMAMemoryTool"

if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

# ── dma_memory import ──────────────────────────────────────────────────────────
try:
    from dma_memory import (               # type: ignore
        DMADevice, DataType, ScanType, MemoryScanner,
        DEVICE_FPGA, DEVICE_NATIVE, DEVICE_FILE,
    )
    from dma_memory.types import encode, decode, type_size  # type: ignore
    HAS_DMA  = True
    _DMA_ERR = ""
except ImportError as _e:
    HAS_DMA  = False
    _DMA_ERR = str(_e)

# ── colour palette (Catppuccin Mocha dark) ─────────────────────────────────────
C = dict(
    base    = "#1e1e2e",
    mantle  = "#181825",
    crust   = "#11111b",
    srf0    = "#313244",
    srf1    = "#45475a",
    srf2    = "#585b70",
    text    = "#cdd6f4",
    sub     = "#a6adc8",
    blue    = "#89b4fa",
    green   = "#a6e3a1",
    red     = "#f38ba8",
    yellow  = "#f9e2af",
    mauve   = "#cba6f7",
    teal    = "#94e2d5",
    peach   = "#fab387",
    sky     = "#89dceb",
)

_DATA_TYPES  = ["int8","int16","int32","int64",
                "uint8","uint16","uint32","uint64",
                "float","double","string_utf8","string_utf16","bytes"]
_SCAN_MODES  = ["Exact","Range","Unknown / First Scan",
                "Increased","Decreased","Changed","Unchanged"]
_DEVICES     = ["fpga","usb3380","native","file"]
_LIVE_DELAY  = 0.5   # seconds between live address-list refreshes


# ── helpers ────────────────────────────────────────────────────────────────────

def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, (bytes, bytearray)):
        return v[:16].hex(" ").upper()
    return str(v)

def _parse_val(s: str, dt: "DataType") -> Any:
    if dt in (DataType.FLOAT, DataType.DOUBLE):
        return float(s)
    if dt in (DataType.STRING_UTF8, DataType.STRING_UTF16):
        return s
    if dt == DataType.BYTES:
        return bytes.fromhex(s.replace(" ",""))
    return int(s, 0)

def _tsz(dt: "DataType") -> int:
    try:
        return type_size(dt)
    except Exception:
        return 4


# ── AddressEntry ───────────────────────────────────────────────────────────────

class AddressEntry:
    """One row in the saved address list with optional freeze."""

    def __init__(self, address: int, value: Any, dtype: "DataType",
                 label: str = "") -> None:
        self.address = address
        self.value   = value
        self.dtype   = dtype
        self.label   = label
        self.frozen  = False
        self._fval: Any = None
        self._fstop = threading.Event()

    def freeze(self, proc: Any) -> None:
        if self.frozen:
            return
        self.frozen = True
        self._fval  = self.value
        self._fstop.clear()
        threading.Thread(target=self._loop, args=(proc,), daemon=True).start()

    def thaw(self) -> None:
        self._fstop.set()
        self.frozen = False

    def _loop(self, proc: Any) -> None:
        while not self._fstop.wait(0.05):
            try:
                proc.write(self.address, encode(self._fval, self.dtype))
            except Exception:
                pass


# ── main application ───────────────────────────────────────────────────────────

class MemEditApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("MemEdit  —  DMA Memory Editor")
        self.geometry("1280x820")
        self.minsize(960, 640)
        self.configure(bg=C["base"])

        # runtime state
        self._dev:      Optional[Any] = None
        self._proc:     Optional[Any] = None
        self._scanner:  Optional[Any] = None
        self._results:  Optional[Any] = None
        self._rdtype:   Optional[Any] = None   # dtype of last scan
        self._procs:    List[Dict]    = []
        self._addrs:    List[AddressEntry] = []
        self._live_running = False

        self._apply_styles()
        self._build()
        self._set_status("Not connected — pick a device and click Connect.")

    # ── styles ─────────────────────────────────────────────────────────────────

    def _apply_styles(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        bg, b2, b3 = C["base"], C["srf0"], C["srf1"]
        fg, sub    = C["text"], C["sub"]
        acc        = C["blue"]
        font_n     = ("Consolas", 10)
        font_b     = ("Consolas", 10, "bold")

        s.configure(".",
            background=bg, foreground=fg, fieldbackground=b2,
            borderwidth=0, focuscolor=acc, font=font_n)
        for w in ("TFrame","TLabelframe","TLabelframe.Label"):
            s.configure(w, background=bg, foreground=acc)
        s.configure("TLabelframe.Label", font=font_b)
        s.configure("TLabel", background=bg, foreground=fg)
        s.configure("TEntry",
            fieldbackground=b2, foreground=fg, insertbackground=fg,
            borderwidth=1, relief="flat", padding=4)
        s.configure("TCombobox",
            fieldbackground=b2, foreground=fg, background=b2,
            selectbackground=acc, arrowcolor=fg, borderwidth=1)
        s.configure("TButton",
            background=b3, foreground=fg, borderwidth=0,
            padding=(8,4), relief="flat", font=font_n)
        s.map("TButton",
            background=[("active",C["srf2"]),("disabled",b2)],
            foreground=[("disabled",C["srf2"])])
        s.configure("Accent.TButton",
            background=acc, foreground=C["base"], font=font_b)
        s.map("Accent.TButton",
            background=[("active",C["teal"]),("pressed",C["sky"])])
        s.configure("Danger.TButton",
            background=C["red"], foreground=C["base"], font=font_b)
        s.map("Danger.TButton",
            background=[("active",C["peach"])])
        s.configure("TNotebook", background=C["mantle"], borderwidth=0)
        s.configure("TNotebook.Tab",
            background=b2, foreground=sub,
            padding=(12,5), font=font_n)
        s.map("TNotebook.Tab",
            background=[("selected",b3)],
            foreground=[("selected",fg)])
        s.configure("Treeview",
            background=b2, foreground=fg, fieldbackground=b2,
            rowheight=22, borderwidth=0, font=font_n)
        s.configure("Treeview.Heading",
            background=b3, foreground=acc, relief="flat", font=font_b)
        s.map("Treeview",
            background=[("selected",acc)],
            foreground=[("selected",C["base"])])
        s.configure("TScrollbar",
            background=b3, troughcolor=b2, arrowcolor=fg, borderwidth=0)
        s.configure("TSeparator", background=C["srf2"])

    # ── layout ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # toolbar
        tb = ttk.Frame(self, padding=(8,5))
        tb.pack(fill="x")
        self._build_toolbar(tb)
        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # content row
        row = ttk.Frame(self)
        row.pack(fill="both", expand=True)

        # left panel
        left = ttk.Frame(row, width=270)
        left.pack(side="left", fill="y", padx=(6,3), pady=6)
        left.pack_propagate(False)
        self._build_left(left)

        ttk.Separator(row, orient="vertical").pack(side="left", fill="y")

        # right notebook
        right = ttk.Frame(row)
        right.pack(side="left", fill="both", expand=True, padx=(3,6), pady=6)
        self._build_right(right)

        # status bar
        self._status = tk.StringVar()
        tk.Label(self, textvariable=self._status,
                 bg=C["mantle"], fg=C["sub"],
                 font=("Consolas",9), anchor="w", padx=8, pady=3
                 ).pack(fill="x", side="bottom")

    # ─ toolbar ─────────────────────────────────────────────────────────────────

    def _build_toolbar(self, p: ttk.Frame) -> None:
        tk.Label(p, text="MemEdit", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",14,"bold")).pack(side="left", padx=(0,14))

        tk.Label(p, text="Device:", bg=C["base"], fg=C["sub"],
                 font=("Consolas",10)).pack(side="left")
        self._dev_var = tk.StringVar(value="fpga")
        ttk.Combobox(p, textvariable=self._dev_var,
                     values=_DEVICES, width=10,
                     state="readonly").pack(side="left", padx=(2,10))

        self._btn_conn = ttk.Button(p, text="⚡ Connect",
                                    style="Accent.TButton",
                                    command=self._do_connect)
        self._btn_conn.pack(side="left", padx=2)

        self._btn_disc = ttk.Button(p, text="✕ Disconnect",
                                    style="Danger.TButton",
                                    command=self._do_disconnect,
                                    state="disabled")
        self._btn_disc.pack(side="left", padx=2)

        self._lbl_conn = tk.Label(p, text="●  Not connected",
                                  bg=C["base"], fg=C["red"],
                                  font=("Consolas",10,"bold"))
        self._lbl_conn.pack(side="left", padx=14)

        self._lbl_proc = tk.Label(p, text="",
                                  bg=C["base"], fg=C["green"],
                                  font=("Consolas",10))
        self._lbl_proc.pack(side="left")

    # ─ left panel ──────────────────────────────────────────────────────────────

    def _build_left(self, p: ttk.Frame) -> None:
        # process browser
        pf = ttk.LabelFrame(p, text=" PROCESSES ", padding=4)
        pf.pack(fill="both", expand=True, pady=(0,4))

        fr = ttk.Frame(pf)
        fr.pack(fill="x", pady=(0,4))
        tk.Label(fr, text="🔍", bg=C["base"], fg=C["sub"],
                 font=("Consolas",10)).pack(side="left")
        self._pfilt = tk.StringVar()
        self._pfilt.trace_add("write", lambda *_: self._filter_procs())
        ttk.Entry(fr, textvariable=self._pfilt).pack(
            side="left", fill="x", expand=True, padx=2)

        cols = ("pid","name")
        self._pt = ttk.Treeview(pf, columns=cols, show="headings",
                                 height=15, selectmode="browse")
        self._pt.heading("pid",  text="PID")
        self._pt.heading("name", text="Name")
        self._pt.column("pid",  width=55, anchor="e", stretch=False)
        self._pt.column("name", width=170)
        psb = ttk.Scrollbar(pf, orient="vertical", command=self._pt.yview)
        self._pt.configure(yscrollcommand=psb.set)
        self._pt.pack(side="left", fill="both", expand=True)
        psb.pack(side="left", fill="y")
        self._pt.bind("<Double-1>", lambda _: self._do_attach())

        br = ttk.Frame(pf)
        br.pack(fill="x", pady=(4,0))
        ttk.Button(br, text="↺ Refresh",
                   command=self._refresh_procs).pack(side="left", padx=2)
        ttk.Button(br, text="⚓ Attach",
                   style="Accent.TButton",
                   command=self._do_attach).pack(side="left", padx=2)

        # frozen list
        ff = ttk.LabelFrame(p, text=" FROZEN ADDRESSES ", padding=4)
        ff.pack(fill="x")
        cols2 = ("addr","val","type")
        self._ft = ttk.Treeview(ff, columns=cols2, show="headings",
                                 height=5, selectmode="browse")
        self._ft.heading("addr", text="Address")
        self._ft.heading("val",  text="Value")
        self._ft.heading("type", text="Type")
        self._ft.column("addr", width=125)
        self._ft.column("val",  width=75)
        self._ft.column("type", width=65)
        self._ft.pack(fill="x")
        ttk.Button(ff, text="✕ Unfreeze Selected",
                   style="Danger.TButton",
                   command=self._thaw_selected).pack(fill="x", pady=(4,0))

    # ─ right notebook ──────────────────────────────────────────────────────────

    def _build_right(self, p: ttk.Frame) -> None:
        self._nb = ttk.Notebook(p)
        self._nb.pack(fill="both", expand=True)

        self._tscan    = ttk.Frame(self._nb)
        self._tresults = ttk.Frame(self._nb)
        self._tmodules = ttk.Frame(self._nb)
        self._tregions = ttk.Frame(self._nb)

        self._nb.add(self._tscan,    text="  🔍 Scan  ")
        self._nb.add(self._tresults, text="  📋 Results  ")
        self._nb.add(self._tmodules, text="  📦 Modules  ")
        self._nb.add(self._tregions, text="  🗺 Regions  ")

        self._build_scan_tab()
        self._build_results_tab()
        self._build_modules_tab()
        self._build_regions_tab()

    # ─ scan tab ────────────────────────────────────────────────────────────────

    def _build_scan_tab(self) -> None:
        pad = ttk.Frame(self._tscan, padding=14)
        pad.pack(fill="both", expand=True)

        def lbl(parent, text, w=10):
            tk.Label(parent, text=text, bg=C["base"], fg=C["sub"],
                     font=("Consolas",10), width=w, anchor="w").pack(side="left")

        # ── numeric scan section ────────────────────────────────────────────
        tk.Label(pad, text="Numeric Scan", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",12,"bold")).pack(anchor="w", pady=(0,8))

        r1 = ttk.Frame(pad); r1.pack(fill="x", pady=3)
        lbl(r1, "Value:")
        self._sval = tk.StringVar()
        ttk.Entry(r1, textvariable=self._sval, width=22).pack(side="left", padx=(0,10))
        lbl(r1, "Type:", w=6)
        self._stype = tk.StringVar(value="int32")
        ttk.Combobox(r1, textvariable=self._stype,
                     values=_DATA_TYPES, width=14,
                     state="readonly").pack(side="left")

        r2 = ttk.Frame(pad); r2.pack(fill="x", pady=3)
        lbl(r2, "Scan mode:")
        self._smode = tk.StringVar(value="Exact")
        ttk.Combobox(r2, textvariable=self._smode,
                     values=_SCAN_MODES, width=22,
                     state="readonly").pack(side="left", padx=(0,10))
        lbl(r2, "Value 2\n(range max):", w=14)
        self._sval2 = tk.StringVar()
        ttk.Entry(r2, textvariable=self._sval2, width=14).pack(side="left")

        r3 = ttk.Frame(pad); r3.pack(fill="x", pady=(6,4))
        self._btn_first = ttk.Button(r3, text="🔍 First Scan",
                                     style="Accent.TButton",
                                     command=self._do_first_scan)
        self._btn_first.pack(side="left", padx=(0,6))
        self._btn_next = ttk.Button(r3, text="🔄 Next Scan",
                                    command=self._do_next_scan,
                                    state="disabled")
        self._btn_next.pack(side="left", padx=(0,6))
        ttk.Button(r3, text="⭮ New Scan",
                   command=self._do_new_scan).pack(side="left")

        self._scan_info = tk.Label(pad, text="", bg=C["base"],
                                   fg=C["yellow"], font=("Consolas",10))
        self._scan_info.pack(anchor="w", pady=(4,0))

        ttk.Separator(pad, orient="horizontal").pack(fill="x", pady=12)

        # ── string / AoB section ────────────────────────────────────────────
        tk.Label(pad, text="String / AoB Search", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",12,"bold")).pack(anchor="w", pady=(0,8))

        rs = ttk.Frame(pad); rs.pack(fill="x", pady=3)
        lbl(rs, "Text / AoB:")
        self._sstr = tk.StringVar()
        ttk.Entry(rs, textvariable=self._sstr, width=34).pack(side="left", padx=(0,8))
        self._senc = tk.StringVar(value="utf16")
        ttk.Combobox(rs, textvariable=self._senc,
                     values=["utf8","utf16"], width=7,
                     state="readonly").pack(side="left")

        rsb = ttk.Frame(pad); rsb.pack(fill="x", pady=3)
        ttk.Button(rsb, text="🔠 Search String",
                   command=self._do_str_search).pack(side="left", padx=(0,6))
        ttk.Button(rsb, text="🔢 AoB Scan (hex: 48 8B ? ? 00)",
                   command=self._do_aob_scan).pack(side="left")

        ttk.Separator(pad, orient="horizontal").pack(fill="x", pady=12)

        # ── pointer chain ────────────────────────────────────────────────────
        tk.Label(pad, text="Pointer Chain Resolver", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",12,"bold")).pack(anchor="w", pady=(0,8))

        rp = ttk.Frame(pad); rp.pack(fill="x", pady=3)
        lbl(rp, "Base addr:")
        self._pbase = tk.StringVar()
        ttk.Entry(rp, textvariable=self._pbase, width=20).pack(side="left", padx=(0,10))
        lbl(rp, "Offsets (0x10,0x50):", w=20)
        self._poffs = tk.StringVar()
        ttk.Entry(rp, textvariable=self._poffs, width=22).pack(side="left")

        rp2 = ttk.Frame(pad); rp2.pack(fill="x", pady=3)
        ttk.Button(rp2, text="🔗 Resolve", command=self._do_resolve).pack(side="left", padx=(0,8))
        self._plbl = tk.Label(rp2, text="", bg=C["base"],
                              fg=C["green"], font=("Consolas",10))
        self._plbl.pack(side="left")

    # ─ results tab ─────────────────────────────────────────────────────────────

    def _build_results_tab(self) -> None:
        top = ttk.Frame(self._tresults, padding=(6,6,6,0))
        top.pack(fill="x")
        self._res_lbl = tk.Label(top, text="0 results", bg=C["base"],
                                 fg=C["sub"], font=("Consolas",10))
        self._res_lbl.pack(side="left")
        ttk.Button(top, text="↺ Refresh values",
                   command=self._refresh_result_vals).pack(side="left", padx=8)
        ttk.Button(top, text="📌 Add selected to list",
                   command=self._add_to_addr_list).pack(side="left", padx=2)

        # scan results tree
        sf = ttk.LabelFrame(self._tresults, text=" Scan Results ", padding=4)
        sf.pack(fill="both", expand=True, padx=6, pady=4)

        rcols = ("address","value","type")
        self._rt = ttk.Treeview(sf, columns=rcols, show="headings",
                                 height=10, selectmode="extended")
        self._rt.heading("address", text="Address")
        self._rt.heading("value",   text="Current Value")
        self._rt.heading("type",    text="Type")
        self._rt.column("address", width=165, anchor="e")
        self._rt.column("value",   width=130)
        self._rt.column("type",    width=110)
        rsb = ttk.Scrollbar(sf, orient="vertical", command=self._rt.yview)
        self._rt.configure(yscrollcommand=rsb.set)
        self._rt.pack(side="left", fill="both", expand=True)
        rsb.pack(side="left", fill="y")
        self._rt.bind("<Double-1>", lambda _: self._edit_result())

        # address list
        af = ttk.LabelFrame(self._tresults, text=" Address List ", padding=4)
        af.pack(fill="both", expand=True, padx=6, pady=(0,6))

        acols = ("address","label","value","type","frozen")
        self._at = ttk.Treeview(af, columns=acols, show="headings",
                                 height=8, selectmode="browse")
        self._at.heading("address", text="Address")
        self._at.heading("label",   text="Label")
        self._at.heading("value",   text="Value")
        self._at.heading("type",    text="Type")
        self._at.heading("frozen",  text="Frozen")
        self._at.column("address", width=155, anchor="e")
        self._at.column("label",   width=120)
        self._at.column("value",   width=110)
        self._at.column("type",    width=95)
        self._at.column("frozen",  width=55, anchor="center")
        asb = ttk.Scrollbar(af, orient="vertical", command=self._at.yview)
        self._at.configure(yscrollcommand=asb.set)
        self._at.pack(side="left", fill="both", expand=True)
        asb.pack(side="left", fill="y")
        self._at.bind("<Double-1>", lambda _: self._edit_addr())

        ab = ttk.Frame(af); ab.pack(fill="x", pady=(4,0))
        ttk.Button(ab, text="✎ Edit",
                   command=self._edit_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="❄ Freeze",
                   command=self._freeze_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="🔥 Thaw",
                   command=self._thaw_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="🏷 Label",
                   command=self._label_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="✕ Remove",
                   style="Danger.TButton",
                   command=self._remove_addr).pack(side="right", padx=2)

    # ─ modules tab ─────────────────────────────────────────────────────────────

    def _build_modules_tab(self) -> None:
        top = ttk.Frame(self._tmodules, padding=(6,6,6,0))
        top.pack(fill="x")
        ttk.Button(top, text="↺ Refresh",
                   command=self._refresh_modules).pack(side="left")

        f = ttk.Frame(self._tmodules, padding=6)
        f.pack(fill="both", expand=True)

        mcols = ("base","size","name","path")
        self._mt = ttk.Treeview(f, columns=mcols, show="headings")
        self._mt.heading("base", text="Base Address")
        self._mt.heading("size", text="Size")
        self._mt.heading("name", text="Name")
        self._mt.heading("path", text="Full Path")
        self._mt.column("base", width=155, anchor="e")
        self._mt.column("size", width=90,  anchor="e")
        self._mt.column("name", width=155)
        self._mt.column("path", width=370)
        msby = ttk.Scrollbar(f, orient="vertical",   command=self._mt.yview)
        msbx = ttk.Scrollbar(f, orient="horizontal", command=self._mt.xview)
        self._mt.configure(yscrollcommand=msby.set, xscrollcommand=msbx.set)
        self._mt.grid(row=0, column=0, sticky="nsew")
        msby.grid(row=0, column=1, sticky="ns")
        msbx.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

    # ─ regions tab ─────────────────────────────────────────────────────────────

    def _build_regions_tab(self) -> None:
        top = ttk.Frame(self._tregions, padding=(6,6,6,0))
        top.pack(fill="x")
        ttk.Button(top, text="↺ Refresh",
                   command=self._refresh_regions).pack(side="left")

        f = ttk.Frame(self._tregions, padding=6)
        f.pack(fill="both", expand=True)

        rcols = ("start","end","size","prot","type","tag")
        self._regt = ttk.Treeview(f, columns=rcols, show="headings")
        self._regt.heading("start", text="Start")
        self._regt.heading("end",   text="End")
        self._regt.heading("size",  text="Size")
        self._regt.heading("prot",  text="Protection")
        self._regt.heading("type",  text="Type")
        self._regt.heading("tag",   text="Tag / Module")
        self._regt.column("start", width=155, anchor="e")
        self._regt.column("end",   width=155, anchor="e")
        self._regt.column("size",  width=100, anchor="e")
        self._regt.column("prot",  width=80)
        self._regt.column("type",  width=80)
        self._regt.column("tag",   width=180)
        rsby = ttk.Scrollbar(f, orient="vertical", command=self._regt.yview)
        self._regt.configure(yscrollcommand=rsby.set)
        self._regt.grid(row=0, column=0, sticky="nsew")
        rsby.grid(row=0, column=1, sticky="ns")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

    # ══════════════════════════════════════════════════════════════════════════
    # Connection
    # ══════════════════════════════════════════════════════════════════════════

    def _do_connect(self) -> None:
        if not HAS_DMA:
            messagebox.showerror(
                "Missing dependency",
                f"dma_memory not importable:\n{_DMA_ERR}\n\npip install memprocfs")
            return
        dev_type = self._dev_var.get()
        self._set_status(f"Connecting to {dev_type}…")
        self._btn_conn.config(state="disabled")

        def _work():
            try:
                dev = DMADevice(dev_type)
                dev.connect()
                self._dev = dev
                self.after(0, self._on_connected)
            except Exception as exc:
                self.after(0, lambda: self._on_conn_fail(str(exc)))

        threading.Thread(target=_work, daemon=True).start()

    def _on_connected(self) -> None:
        self._lbl_conn.config(text="●  Connected", fg=C["green"])
        self._btn_conn.config(state="disabled")
        self._btn_disc.config(state="normal")
        self._set_status(f"Connected to {self._dev_var.get()}")
        self._refresh_procs()

    def _on_conn_fail(self, err: str) -> None:
        self._btn_conn.config(state="normal")
        self._lbl_conn.config(text="●  Error", fg=C["red"])
        self._set_status(f"Connect failed: {err}")
        messagebox.showerror("Connection failed", err)

    def _do_disconnect(self) -> None:
        # thaw everything
        for e in self._addrs:
            e.thaw()
        if self._dev:
            try: self._dev.disconnect()
            except Exception: pass
        self._dev = self._proc = self._scanner = self._results = None
        self._lbl_conn.config(text="●  Not connected", fg=C["red"])
        self._lbl_proc.config(text="")
        self._btn_conn.config(state="normal")
        self._btn_disc.config(state="disabled")
        self._set_status("Disconnected.")

    # ══════════════════════════════════════════════════════════════════════════
    # Process list
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_procs(self) -> None:
        if not self._dev:
            return
        self._set_status("Loading process list…")

        def _work():
            try:
                procs = self._dev.list_processes()
                self.after(0, lambda: self._load_procs(procs))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"Process list error: {exc}"))

        threading.Thread(target=_work, daemon=True).start()

    def _load_procs(self, procs: List[Dict]) -> None:
        self._procs = procs
        self._filter_procs()
        self._set_status(f"{len(procs)} processes.")

    def _filter_procs(self) -> None:
        filt = self._pfilt.get().lower()
        self._pt.delete(*self._pt.get_children())
        for p in self._procs:
            if filt and filt not in p["name"].lower():
                continue
            self._pt.insert("", "end", values=(p["pid"], p["name"]))

    # ══════════════════════════════════════════════════════════════════════════
    # Attach
    # ══════════════════════════════════════════════════════════════════════════

    def _do_attach(self) -> None:
        if not self._dev:
            messagebox.showwarning("Not connected", "Connect first.")
            return
        sel = self._pt.selection()
        if not sel:
            return
        pid, name = self._pt.item(sel[0], "values")
        pid = int(pid)
        self._set_status(f"Attaching to {name} (PID {pid})…")

        def _work():
            try:
                proc    = self._dev.get_process(pid)
                scanner = proc.scanner()
                self.after(0, lambda: self._on_attached(proc, scanner))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"Attach failed: {exc}"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_attached(self, proc: Any, scanner: Any) -> None:
        self._proc    = proc
        self._scanner = scanner
        self._results = None
        self._btn_next.config(state="disabled")
        self._lbl_proc.config(
            text=f"   ⚓  {proc.name}  PID {proc.pid}",
            fg=C["green"])
        self._set_status(f"Attached to {proc.name} (PID {proc.pid})")
        self._refresh_modules()
        self._refresh_regions()
        self._start_live_refresh()

    # ══════════════════════════════════════════════════════════════════════════
    # Scanning
    # ══════════════════════════════════════════════════════════════════════════

    def _need_proc(self) -> bool:
        if not self._proc or not self._scanner:
            messagebox.showwarning("No process", "Attach to a process first.")
            return False
        return True

    def _do_first_scan(self) -> None:
        if not self._need_proc():
            return
        val_str  = self._sval.get().strip()
        type_str = self._stype.get()
        mode_str = self._smode.get()
        val2_str = self._sval2.get().strip()

        try:
            dt = DataType(type_str)
        except ValueError:
            messagebox.showerror("Type", f"Unknown type: {type_str}"); return

        mode_map = {
            "Exact":              ScanType.EXACT,
            "Range":              ScanType.RANGE,
            "Unknown / First Scan": ScanType.UNKNOWN,
            "Increased":          ScanType.INCREASED,
            "Decreased":          ScanType.DECREASED,
            "Changed":            ScanType.CHANGED,
            "Unchanged":          ScanType.UNCHANGED,
        }
        st = mode_map.get(mode_str, ScanType.EXACT)

        if st != ScanType.UNKNOWN and not val_str:
            messagebox.showwarning("Value", "Enter a value to scan for."); return

        try:
            val  = _parse_val(val_str,  dt) if val_str  else 0
            val2 = _parse_val(val2_str, dt) if val2_str else None
        except Exception as exc:
            messagebox.showerror("Parse error", str(exc)); return

        self._rdtype = dt
        self._run_scan(val, dt, st, val2, first=True)

    def _do_next_scan(self) -> None:
        if not self._need_proc() or self._results is None:
            return
        val_str  = self._sval.get().strip()
        mode_str = self._smode.get()
        dt       = self._rdtype

        mode_map = {
            "Exact":     ScanType.EXACT,
            "Range":     ScanType.RANGE,
            "Increased": ScanType.INCREASED,
            "Decreased": ScanType.DECREASED,
            "Changed":   ScanType.CHANGED,
            "Unchanged": ScanType.UNCHANGED,
        }
        st = mode_map.get(mode_str, ScanType.EXACT)

        val = None
        if st in (ScanType.EXACT, ScanType.RANGE):
            if not val_str:
                messagebox.showwarning("Value", "Enter a value."); return
            try:
                val = _parse_val(val_str, dt)
            except Exception as exc:
                messagebox.showerror("Parse error", str(exc)); return

        prev = self._results
        self._btn_first.config(state="disabled")
        self._btn_next.config(state="disabled")
        self._scan_info.config(text="⏳ Filtering…", fg=C["yellow"])

        def _work():
            try:
                t0 = time.time()
                res = self._scanner.next_scan(prev, val, st)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda: self._on_scan_err(str(exc)))

        threading.Thread(target=_work, daemon=True).start()

    def _do_new_scan(self) -> None:
        self._results = None
        self._btn_next.config(state="disabled")
        self._scan_info.config(text="", fg=C["yellow"])
        self._rt.delete(*self._rt.get_children())
        self._res_lbl.config(text="0 results")

    def _run_scan(self, val: Any, dt: "DataType", st: "ScanType",
                  val2: Any, first: bool) -> None:
        self._btn_first.config(state="disabled")
        self._btn_next.config(state="disabled")
        self._scan_info.config(text="⏳ Scanning…", fg=C["yellow"])

        def _work():
            try:
                t0 = time.time()
                res = self._scanner.scan(val, dt, st, value2=val2)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda: self._on_scan_err(str(exc)))

        threading.Thread(target=_work, daemon=True).start()

    def _on_scan_done(self, results: Any, elapsed: float) -> None:
        self._results = results
        n = len(results)
        self._scan_info.config(
            text=f"✔  {n:,} results in {elapsed:.2f}s", fg=C["green"])
        self._res_lbl.config(text=f"{n:,} results")
        self._btn_first.config(state="normal")
        self._btn_next.config(state="normal" if n > 0 else "disabled")
        self._populate_results(results)
        self._nb.select(self._tresults)

    def _on_scan_err(self, err: str) -> None:
        self._scan_info.config(text=f"✗  {err}", fg=C["red"])
        self._btn_first.config(state="normal")
        self._btn_next.config(state="normal" if self._results else "disabled")

    def _do_str_search(self) -> None:
        if not self._need_proc(): return
        text = self._sstr.get().strip()
        if not text:
            messagebox.showwarning("Empty", "Enter a string."); return
        enc = self._senc.get()
        dt  = DataType.STRING_UTF8 if enc == "utf8" else DataType.STRING_UTF16
        self._rdtype = dt
        self._scan_info.config(text="⏳ String search…", fg=C["yellow"])
        self._btn_first.config(state="disabled")

        def _work():
            try:
                t0  = time.time()
                res = self._scanner.search_string(text, dt)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda: self._on_scan_err(str(exc)))

        threading.Thread(target=_work, daemon=True).start()

    def _do_aob_scan(self) -> None:
        if not self._need_proc(): return
        pattern = self._sstr.get().strip()
        if not pattern:
            messagebox.showwarning("Empty", "Enter hex bytes e.g. 48 8B ? ? 00"); return
        self._rdtype = DataType.BYTES
        self._scan_info.config(text="⏳ AoB scan…", fg=C["yellow"])
        self._btn_first.config(state="disabled")

        def _work():
            try:
                t0  = time.time()
                res = self._scanner.search_aob(pattern)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda: self._on_scan_err(str(exc)))

        threading.Thread(target=_work, daemon=True).start()

    def _do_resolve(self) -> None:
        if not self._need_proc(): return
        base_str = self._pbase.get().strip()
        offs_str = self._poffs.get().strip()
        if not base_str:
            messagebox.showwarning("Empty", "Enter a base address."); return
        try:
            base    = int(base_str, 0)
            offsets = [int(o.strip(), 16) for o in offs_str.split(",") if o.strip()]
        except ValueError as exc:
            messagebox.showerror("Parse error", str(exc)); return
        result = self._proc.resolve_pointer_chain(base, offsets)
        if result is None:
            self._plbl.config(text="null pointer encountered", fg=C["red"])
        else:
            self._plbl.config(text=f"→  0x{result:016X}", fg=C["green"])

    # ══════════════════════════════════════════════════════════════════════════
    # Results
    # ══════════════════════════════════════════════════════════════════════════

    def _populate_results(self, results: Any) -> None:
        self._rt.delete(*self._rt.get_children())
        if not self._proc or self._rdtype is None:
            return
        dt  = self._rdtype
        MAX = 2000
        for m in results._matches[:MAX]:
            try:
                raw = self._proc.read(m.address, _tsz(dt))
                val = _fmt(decode(raw, dt)) if raw else "?"
            except Exception:
                val = "?"
            self._rt.insert("", "end",
                values=(f"0x{m.address:016X}", val, dt.value))
        if len(results) > MAX:
            self._rt.insert("", "end",
                values=(f"… {len(results)-MAX:,} more results", "", ""))

    def _refresh_result_vals(self) -> None:
        if not self._proc or self._rdtype is None:
            return
        dt = self._rdtype
        for iid in self._rt.get_children():
            v = self._rt.item(iid, "values")
            if not v[0].startswith("0x"):
                continue
            try:
                addr = int(v[0], 16)
                raw  = self._proc.read(addr, _tsz(dt))
                val  = _fmt(decode(raw, dt)) if raw else "?"
                self._rt.item(iid, values=(v[0], val, v[2]))
            except Exception:
                pass

    def _edit_result(self) -> None:
        if not self._proc: return
        sel = self._rt.selection()
        if not sel: return
        v = self._rt.item(sel[0], "values")
        if not v[0].startswith("0x"): return
        addr = int(v[0], 16)
        dt   = self._rdtype
        new  = simpledialog.askstring(
            "Edit value", f"New value for {v[0]}:", parent=self)
        if new is None: return
        try:
            val = _parse_val(new, dt)
            ok  = self._proc.write(addr, encode(val, dt))
            if ok:
                self._rt.item(sel[0], values=(v[0], _fmt(val), dt.value))
                self._set_status(f"Written 0x{addr:016X} = {_fmt(val)}")
            else:
                messagebox.showerror("Write failed", f"Could not write to {v[0]}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _add_to_addr_list(self) -> None:
        sel = self._rt.selection()
        if not sel:
            messagebox.showinfo("None selected",
                "Select one or more rows in Scan Results first."); return
        dt  = self._rdtype
        added = 0
        for iid in sel:
            v = self._rt.item(iid, "values")
            if not v[0].startswith("0x"): continue
            addr = int(v[0], 16)
            if any(e.address == addr for e in self._addrs): continue
            try:
                raw = self._proc.read(addr, _tsz(dt)) if self._proc else b""
                val = decode(raw, dt) if raw else 0
            except Exception:
                val = 0
            self._addrs.append(AddressEntry(addr, val, dt))
            added += 1
        self._refresh_addr_tree()
        self._set_status(f"Added {added} address(es) to list.")

    # ── address list ────────────────────────────────────────────────────────────

    def _refresh_addr_tree(self) -> None:
        self._at.delete(*self._at.get_children())
        self._ft.delete(*self._ft.get_children())
        for e in self._addrs:
            if self._proc:
                try:
                    raw = self._proc.read(e.address, _tsz(e.dtype))
                    if raw:
                        e.value = decode(raw, e.dtype)
                except Exception:
                    pass
            fz = "❄" if e.frozen else ""
            self._at.insert("", "end",
                values=(f"0x{e.address:016X}", e.label,
                        _fmt(e.value), e.dtype.value, fz))
            if e.frozen:
                self._ft.insert("", "end",
                    values=(f"0x{e.address:016X}",
                            _fmt(e._fval), e.dtype.value))

    def _edit_addr(self) -> None:
        if not self._proc: return
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        e   = self._addrs[idx]
        new = simpledialog.askstring(
            "Edit value", f"New value for 0x{e.address:016X}:", parent=self)
        if new is None: return
        try:
            val = _parse_val(new, e.dtype)
            ok  = self._proc.write(e.address, encode(val, e.dtype))
            if ok:
                e.value = val
                if e.frozen: e._fval = val
                self._refresh_addr_tree()
            else:
                messagebox.showerror("Write failed",
                    f"Could not write to 0x{e.address:016X}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _freeze_addr(self) -> None:
        if not self._proc: return
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        self._addrs[idx].freeze(self._proc)
        self._refresh_addr_tree()

    def _thaw_addr(self) -> None:
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        self._addrs[idx].thaw()
        self._refresh_addr_tree()

    def _thaw_selected(self) -> None:
        sel = self._ft.selection()
        if not sel: return
        addr_str = self._ft.item(sel[0], "values")[0]
        addr = int(addr_str, 16)
        for e in self._addrs:
            if e.address == addr:
                e.thaw(); break
        self._refresh_addr_tree()

    def _label_addr(self) -> None:
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        e   = self._addrs[idx]
        lbl = simpledialog.askstring("Label", f"Label for 0x{e.address:016X}:",
                                     parent=self, initialvalue=e.label)
        if lbl is not None:
            e.label = lbl
            self._refresh_addr_tree()

    def _remove_addr(self) -> None:
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        self._addrs[idx].thaw()
        self._addrs.pop(idx)
        self._refresh_addr_tree()

    # ══════════════════════════════════════════════════════════════════════════
    # Modules
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_modules(self) -> None:
        if not self._proc: return
        self._mt.delete(*self._mt.get_children())
        try:
            for m in sorted(self._proc.modules(), key=lambda x: x.name.lower()):
                self._mt.insert("", "end",
                    values=(f"0x{m.base:016X}", f"0x{m.size:08X}",
                            m.name, m.path))
        except Exception as exc:
            self._set_status(f"Modules error: {exc}")

    # ══════════════════════════════════════════════════════════════════════════
    # Regions
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_regions(self) -> None:
        if not self._proc: return
        self._regt.delete(*self._regt.get_children())
        try:
            for r in self._proc.memory_regions():
                self._regt.insert("", "end",
                    values=(f"0x{r['va_start']:016X}",
                            f"0x{r['va_end']:016X}",
                            f"0x{r['size']:X}",
                            r.get("protection",""),
                            r.get("type",""),
                            r.get("tag","")))
        except Exception as exc:
            self._set_status(f"Regions error: {exc}")

    # ══════════════════════════════════════════════════════════════════════════
    # Live address-list refresh
    # ══════════════════════════════════════════════════════════════════════════

    def _start_live_refresh(self) -> None:
        if self._live_running:
            return
        self._live_running = True

        def _loop():
            while self._live_running and self._proc:
                self.after(0, self._refresh_addr_tree)
                time.sleep(_LIVE_DELAY)

        threading.Thread(target=_loop, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _set_status(self, msg: str) -> None:
        self._status.set(msg)

    def destroy(self) -> None:
        self._live_running = False
        for e in self._addrs:
            e.thaw()
        super().destroy()


# ── entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    if not HAS_DMA:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Missing dependency",
            f"dma_memory could not be imported:\n{_DMA_ERR}\n\npip install memprocfs")
        root.destroy()
        return
    app = MemEditApp()
    app.mainloop()


if __name__ == "__main__":
    main()
