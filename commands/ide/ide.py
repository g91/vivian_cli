"""ide command — mirrors src/commands/ide/ide.tsx.

Open the current project in an IDE (VS Code, Cursor, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    import subprocess, os
    ide = args.strip().lower() if args else "code"
    cwd = os.getcwd()
    commands = {"code": ["code", "."], "cursor": ["cursor", "."], "windsurf": ["windsurf", "."]}
    cmd = commands.get(ide, ["code", "."])
    try:
        subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return TextResult(f"Opening in {ide}...")
    except Exception as e:
        return TextResult(f"Failed to open {ide}: {e}")


ideInfo = call
ide_info = call
