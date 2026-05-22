"""keybindings command — mirrors src/commands/keybindings/keybindings.ts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ...keybindings.loadUserBindings import (
    getKeybindingsPath,
    isKeybindingCustomizationEnabled,
)
from ...keybindings.template import generateKeybindingsTemplate

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def _open_in_editor(path: str) -> str | None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    commands: list[list[str]] = []
    if editor:
        commands.append([editor, path])
    elif sys.platform == "darwin":
        commands.append(["open", path])
    elif sys.platform.startswith("linux"):
        commands.append(["xdg-open", path])
    elif sys.platform == "win32":
        commands.append(["cmd", "/c", "start", "", path])

    for command in commands:
        try:
            subprocess.Popen(command)
            return None
        except Exception as exc:
            last_error = str(exc)
    return locals().get("last_error", "No editor command available")


def formatKeybindings(bindings: dict | None = None) -> str:
    from ...utils.keybindings import KeybindingManager

    manager = KeybindingManager()
    return manager.format_bindings()


async def call(args: str = "", context: CommandContext | None = None) -> TextResult:
    from ...types.command import TextResult

    if not isKeybindingCustomizationEnabled():
        return TextResult(
            "Keybinding customization is not enabled. This feature is currently in preview."
        )

    keybindings_path = Path(getKeybindingsPath())
    keybindings_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = True
    try:
        with open(keybindings_path, "x", encoding="utf-8") as handle:
            handle.write(generateKeybindingsTemplate())
        file_exists = False
    except FileExistsError:
        file_exists = True

    open_error = _open_in_editor(str(keybindings_path))
    if open_error:
        action = "Opened" if file_exists else "Created"
        return TextResult(
            f"{action} {keybindings_path}. Could not open in editor: {open_error}"
        )

    if file_exists:
        return TextResult(f"Opened {keybindings_path} in your editor.")
    return TextResult(
        f"Created {keybindings_path} with template. Opened in your editor."
    )


format_keybindings = formatKeybindings
