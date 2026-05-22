"""Port of src/ink/terminal.ts - Terminal capability detection."""
from __future__ import annotations

import os
import sys
from typing import Any

from .clearTerminal import getClearTerminalSequence
from .frame import Diff
from .termio.csi import cursorMove, cursorTo, eraseLines
from .termio.dec import BSU, ESU, HIDE_CURSOR, SHOW_CURSOR
from .termio.osc import link

_xtversion_name: str | None = None
SYNC_OUTPUT_SUPPORTED = False


def _isSynchronizedOutputSupported() -> bool:
    if os.environ.get("TMUX"):
        return False
    tp = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")
    if tp in ("iTerm.app", "WezTerm", "WarpTerminal", "ghostty", "contour", "vscode", "alacritty"):
        return True
    if "kitty" in term or os.environ.get("KITTY_WINDOW_ID"):
        return True
    if term == "xterm-ghostty":
        return True
    if term.startswith("foot") if term else False:
        return True
    if "alacritty" in term:
        return True
    if os.environ.get("ZED_TERM"):
        return True
    if os.environ.get("WT_SESSION"):
        return True
    vte = os.environ.get("VTE_VERSION", "")
    if vte and vte.isdigit() and int(vte) >= 6800:
        return True
    return False


SYNC_OUTPUT_SUPPORTED = _isSynchronizedOutputSupported()


def setXtversionName(name: str) -> None:
    global _xtversion_name
    if _xtversion_name is None:
        _xtversion_name = name


def isXtermJs() -> bool:
    if os.environ.get("TERM_PROGRAM") == "vscode":
        return True
    return (_xtversion_name or "").startswith("xterm.js")


def isProgressReportingAvailable() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.environ.get("WT_SESSION"):
        return False
    if os.environ.get("ConEmuANSI") or os.environ.get("ConEmuPID"):
        return True
    tp = os.environ.get("TERM_PROGRAM", "")
    tv = os.environ.get("TERM_PROGRAM_VERSION", "")
    if tp == "ghostty" and tv:
        return True
    if tp == "iTerm.app" and tv:
        return True
    return False


def supportsExtendedKeys() -> bool:
    tp = os.environ.get("TERM_PROGRAM", "")
    return tp in ("iTerm.app", "kitty", "WezTerm", "ghostty", "tmux", "windows-terminal")


def hasCursorUpViewportYankBug() -> bool:
    return sys.platform == "win32" or bool(os.environ.get("WT_SESSION"))


def writeDiffToTerminal(stdout: Any, diff: Diff, skipSyncMarkers: bool = False) -> None:
    if not diff:
        return
    useSync = not skipSyncMarkers
    buffer = BSU if useSync else ""

    for patch in diff:
        t = patch["type"]
        if t == "stdout":
            buffer += patch.get("content", "")
        elif t == "clear":
            if patch.get("count", 0) > 0:
                buffer += eraseLines(patch["count"])
        elif t == "clearTerminal":
            buffer += getClearTerminalSequence()
        elif t == "cursorHide":
            buffer += HIDE_CURSOR
        elif t == "cursorShow":
            buffer += SHOW_CURSOR
        elif t == "cursorMove":
            buffer += cursorMove(patch.get("x", 0), patch.get("y", 0))
        elif t == "cursorTo":
            buffer += cursorTo(patch.get("col", 0))
        elif t == "carriageReturn":
            buffer += "\r"
        elif t == "hyperlink":
            buffer += link(patch.get("uri", ""))
        elif t == "styleStr":
            buffer += patch.get("str", "")

    if useSync:
        buffer += ESU
    stdout.write(buffer)
    stdout.flush()
