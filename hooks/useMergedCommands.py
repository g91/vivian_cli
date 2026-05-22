"""Port of src/hooks/useMergedCommands.ts."""
from __future__ import annotations

from typing import Any


def useMergedCommands(initialCommands: list[dict], mcpCommands: list[dict]) -> list[dict]:
    if len(mcpCommands) == 0:
        return initialCommands
    merged = [*initialCommands, *mcpCommands]
    seen: set[Any] = set()
    out: list[dict] = []
    for cmd in merged:
        key = cmd.get('name') if isinstance(cmd, dict) else None
        if key in seen:
            continue
        seen.add(key)
        out.append(cmd)
    return out
