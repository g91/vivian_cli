"""terminal-setup command — mirrors src/commands/terminalSetup/.

Configure terminal integration (shell aliases, PS1, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    import os, shutil
    shell = os.environ.get("SHELL", "/bin/bash")
    rc_file = ""
    if "zsh" in shell:
        rc_file = os.path.expanduser("~/.zshrc")
    elif "bash" in shell:
        rc_file = os.path.expanduser("~/.bashrc")
    if rc_file and os.path.exists(rc_file):
        return TextResult(f"Terminal config found: {rc_file}\nShell: {shell}")
    return TextResult(f"Terminal setup: Shell={shell}. No rc file found.")


setupTerminal = call
setup_terminal = call
