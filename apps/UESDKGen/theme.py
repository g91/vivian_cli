"""theme.py — Catppuccin Mocha colour palette + ttk theme for UESDKGen."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict

# ─────────────────────────────────────────────────────────────────────────────
# Catppuccin Mocha colour palette
# ─────────────────────────────────────────────────────────────────────────────
C: Dict[str, str] = {
    "base":      "#1e1e2e", "mantle":   "#181825", "crust":    "#11111b",
    "srf0":      "#313244", "srf1":     "#45475a", "srf2":     "#585b70",
    "text":      "#cdd6f4", "subtext0": "#a6adc8", "subtext1": "#bac2de",
    "blue":      "#89b4fa", "lavender": "#b4befe", "sapphire": "#74c7ec",
    "sky":       "#89dceb", "teal":     "#94e2d5", "green":    "#a6e3a1",
    "yellow":    "#f9e2af", "peach":    "#fab387", "maroon":   "#eba0ac",
    "red":       "#f38ba8", "mauve":    "#cba6f7", "pink":     "#f5c2e7",
    "flamingo":  "#f2cdcd", "rosewater":"#f5e0dc",
}


def apply_theme(root: tk.Tk) -> None:
    """Apply Catppuccin Mocha theme to all ttk widgets."""
    s = ttk.Style(root)
    s.theme_use("clam")
    bg, srf0, srf1 = C["base"], C["srf0"], C["srf1"]
    fg, sub        = C["text"], C["subtext0"]
    blue           = C["blue"]

    s.configure(".",
        background=bg, foreground=fg, troughcolor=srf0,
        bordercolor=srf0, darkcolor=bg, lightcolor=srf0,
        selectbackground=blue, selectforeground=bg,
        fieldbackground=srf0, font=("Consolas", 10))

    for w in ("TFrame", "TLabelframe", "TLabelframe.Label", "TLabel",
              "TButton", "TEntry", "TCombobox", "TCheckbutton",
              "TScrollbar", "Treeview", "Treeview.Heading",
              "TNotebook", "TNotebook.Tab", "Horizontal.TProgressbar"):
        s.configure(w, background=bg, foreground=fg,
                    bordercolor=srf0, relief="flat")

    s.configure("TButton",
        background=srf0, foreground=fg, bordercolor=srf1,
        focusthickness=0, relief="flat", padding=(8, 4))
    s.map("TButton",
        background=[("active", srf1), ("pressed", srf1)])

    s.configure("Accent.TButton",
        background=blue, foreground=bg, padding=(8, 4))
    s.map("Accent.TButton",
        background=[("active", C["lavender"]), ("pressed", C["sapphire"])])

    s.configure("TEntry",
        fieldbackground=srf0, foreground=fg,
        insertcolor=fg, bordercolor=srf1, relief="flat")

    s.configure("TCombobox",
        fieldbackground=srf0, background=srf0,
        foreground=fg, arrowcolor=fg, bordercolor=srf1)

    s.configure("TNotebook", tabmargins=[2, 4, 0, 0])
    s.configure("TNotebook.Tab",
        background=srf0, foreground=sub, padding=[12, 4], focusthickness=0)
    s.map("TNotebook.Tab",
        background=[("selected", bg)],
        foreground=[("selected", fg)])

    s.configure("Treeview",
        background=C["mantle"], foreground=fg,
        rowheight=22, fieldbackground=C["mantle"], bordercolor=srf0)
    s.configure("Treeview.Heading",
        background=srf0, foreground=sub, relief="flat", padding=(4, 2))
    s.map("Treeview",
        background=[("selected", blue)],
        foreground=[("selected", bg)])

    s.configure("TScrollbar",
        background=srf0, troughcolor=bg, arrowcolor=sub,
        arrowsize=12, relief="flat")
    s.map("TScrollbar", background=[("active", srf1)])

    s.configure("TLabelframe", background=bg, bordercolor=srf1, relief="groove")
    s.configure("TLabelframe.Label",
        background=bg, foreground=C["blue"], font=("Consolas", 9, "bold"))

    s.configure("Horizontal.TProgressbar",
        background=blue, troughcolor=srf0, bordercolor=srf0)
