"""External editor helpers mirroring src/utils/editor.ts."""

from __future__ import annotations

import os
import platform
import re
import shlex
import shutil
import subprocess
from functools import lru_cache

from .debug import logForDebugging

GUI_EDITORS = [
    "code",
    "cursor",
    "windsurf",
    "codium",
    "subl",
    "atom",
    "gedit",
    "notepad++",
    "notepad",
]
PLUS_N_EDITORS = re.compile(r"\b(vi|vim|nvim|nano|emacs|pico|micro|helix|hx)\b")
VSCODE_FAMILY = {"code", "cursor", "windsurf", "codium"}


def _basename_from_editor(editor: str) -> str:
    first = shlex.split(editor)[0] if editor else ""
    return os.path.basename(first)


def isCommandAvailable(command):
    return bool(command) and shutil.which(str(command)) is not None


def classifyGuiEditor(editor):
    """Classify the editor as GUI or not. Returns the matched GUI family name."""
    base = _basename_from_editor(str(editor or "")).lower()
    for gui in GUI_EDITORS:
        if gui in base:
            return gui
    return None


def guiGotoArgv(guiFamily, filePath, line):
    """Build goto-line argv for a GUI editor. VS Code family uses -g file:line."""
    if not line:
        return [filePath]
    if guiFamily in VSCODE_FAMILY:
        return ["-g", f"{filePath}:{line}"]
    if guiFamily == "subl":
        return [f"{filePath}:{line}"]
    return [filePath]


def _editor_parts(editor: str) -> tuple[str, list[str]]:
    parts = shlex.split(editor)
    if not parts:
        return editor, []
    return parts[0], parts[1:]


def openFileInExternalEditor(filePath, line=None):
    """Launch a file in the user's external editor."""
    editor = getExternalEditor()
    if not editor:
        return False

    base, editor_args = _editor_parts(editor)
    gui_family = classifyGuiEditor(editor)

    if gui_family:
        goto_argv = guiGotoArgv(gui_family, filePath, line)
        try:
            if platform.system().lower() == "windows":
                command = " ".join([editor, *[shlex.quote(arg) for arg in goto_argv]])
                process = subprocess.Popen(command, shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                process = subprocess.Popen([base, *editor_args, *goto_argv], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            process.poll()
            return True
        except Exception as error:
            logForDebugging(f"editor spawn failed: {error}", {"level": "error"})
            return False

    use_goto_line = bool(line) and PLUS_N_EDITORS.search(_basename_from_editor(base)) is not None
    try:
        if platform.system().lower() == "windows":
            line_arg = f"+{line} " if use_goto_line else ""
            command = f"{editor} {line_arg}{shlex.quote(filePath)}"
            completed = subprocess.run(command, shell=True, check=False)
        else:
            args = [*editor_args, *([f"+{line}"] if use_goto_line else []), filePath]
            completed = subprocess.run([base, *args], check=False)
        return completed.returncode == 0
    except Exception as error:
        logForDebugging(f"editor spawn failed: {error}", {"level": "error"})
        return False


@lru_cache(maxsize=1)
def getExternalEditor():
    for key in ("VISUAL", "EDITOR"):
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()

    if platform.system().lower() == "windows":
        return "start /wait notepad"

    for command in ("code", "vi", "nano"):
        if isCommandAvailable(command):
            return command
    return None


is_command_available = isCommandAvailable
classify_gui_editor = classifyGuiEditor
gui_goto_argv = guiGotoArgv
open_file_in_external_editor = openFileInExternalEditor
get_external_editor = getExternalEditor

