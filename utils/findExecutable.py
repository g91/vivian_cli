"""Find executable on PATH — mirrors src/utils/findExecutable.ts"""
from __future__ import annotations

from .which import which_sync


def find_executable(exe: str, args: list[str]) -> dict[str, object]:
    """Return {'cmd': resolved_path_or_exe, 'args': args} for the given executable."""
    resolved = which_sync(exe)
    return {"cmd": resolved if resolved else exe, "args": args}
