"""heapdump command — mirrors src/commands/heapdump/heapdump.ts.

Generate a heap dump for memory debugging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def takeHeapdump() -> str:
    """Take a heap dump."""
    import os, sys, time
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.expanduser(f"~/.vivian/heapdump_{ts}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        import json, gc
        stats = {
            "python_version": sys.version,
            "gc_stats": gc.get_stats(),
            "gc_count": gc.get_count(),
            "object_count": len(gc.get_objects()),
        }
        with open(path, "w") as f:
            json.dump(stats, f, indent=2, default=str)
        return f"Heap dump saved to: {path}"
    except Exception as e:
        return f"Heap dump failed: {e}"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult(takeHeapdump())


take_heapdump = takeHeapdump
