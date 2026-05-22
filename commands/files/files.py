"""files command — mirrors src/commands/files/files.ts.

Lists files currently in the conversation context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import os

from ...utils.cwd import get_cwd
from ...utils.fileStateCache import cacheKeys

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult

    read_file_state = getattr(context, "readFileState", None)
    if read_file_state is None:
        read_file_state = getattr(context, "read_file_state", None)

    try:
        if read_file_state is None:
            files: list[str] = []
        elif isinstance(read_file_state, dict):
            files = list(read_file_state.keys())
        else:
            files = cacheKeys(read_file_state)
    except Exception:
        files = []

    if not files:
        return TextResult("No files in context")

    cwd = get_cwd()
    rendered = []
    for file_path in files:
        try:
            rendered.append(os.path.relpath(file_path, cwd))
        except Exception:
            rendered.append(str(file_path))

    return TextResult("Files in context:\n" + "\n".join(rendered))


showFiles = call
show_files = call
