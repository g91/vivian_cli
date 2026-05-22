"""Port of src/ink/useTerminalNotification.ts."""
from __future__ import annotations

import sys
from typing import Any, Callable

from .terminal import isProgressReportingAvailable
from .termio.ansi import BEL
from .termio.osc import osc, wrapForMultiplexer

OSC_ITERM2 = 1337
OSC_KITTY = 99
OSC_GHOSTTY = 777


def _notifyITerm2(message: str, title: str | None = None) -> None:
    display = f"{title}:\n{message}" if title else message
    sys.stdout.write(wrapForMultiplexer(osc(OSC_ITERM2, f"\n\n{display}")))
    sys.stdout.flush()


def _notifyKitty(message: str, title: str, id: int) -> None:
    sys.stdout.write(wrapForMultiplexer(osc(OSC_KITTY, f"i={id}:d=0:p=title", title)))
    sys.stdout.write(wrapForMultiplexer(osc(OSC_KITTY, f"i={id}:p=body", message)))
    sys.stdout.write(wrapForMultiplexer(osc(OSC_KITTY, f"i={id}:d=1:a=focus", "")))
    sys.stdout.flush()


def _notifyGhostty(message: str, title: str) -> None:
    sys.stdout.write(wrapForMultiplexer(osc(OSC_GHOSTTY, "notify", title, message)))
    sys.stdout.flush()


def _notifyBell() -> None:
    sys.stdout.write(BEL)
    sys.stdout.flush()


def _progress(state: str | None, percentage: int | None = None) -> None:
    if not isProgressReportingAvailable():
        return
    if not state:
        sys.stdout.write(wrapForMultiplexer(osc(OSC_ITERM2, "Progress", "Clear", "")))
        sys.stdout.flush()
        return
    pct = max(0, min(100, round(percentage or 0)))
    if state == "completed":
        sys.stdout.write(wrapForMultiplexer(osc(OSC_ITERM2, "Progress", "Clear", "")))
    elif state == "error":
        sys.stdout.write(wrapForMultiplexer(osc(OSC_ITERM2, "Progress", "Error", pct)))
    elif state == "indeterminate":
        sys.stdout.write(wrapForMultiplexer(osc(OSC_ITERM2, "Progress", "Indeterminate", "")))
    elif state == "running":
        sys.stdout.write(wrapForMultiplexer(osc(OSC_ITERM2, "Progress", "Set", pct)))
    sys.stdout.flush()
