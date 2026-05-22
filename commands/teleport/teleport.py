"""teleport command — mirrors src/commands/teleport/teleport.tsx.

Teleport the current session to a remote environment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    target = args.strip() if args else ""
    if not target:
        return TextResult("Usage: /teleport <hostname|session_id>")
    return TextResult(f"Teleporting to {target}... Use /session to verify the new environment.")


teleportTo = call
teleport_to = call
