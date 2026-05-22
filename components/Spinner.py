"""Spinner component — minimal port of src/components/Spinner.tsx."""

from __future__ import annotations


SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]


def Spinner(frame: int = 0) -> str:
    return SPINNER_FRAMES[frame % len(SPINNER_FRAMES)]


__all__ = ["Spinner", "SPINNER_FRAMES"]