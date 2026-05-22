"""Prompt editor helpers mirroring src/utils/promptEditor.ts."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .editor import classifyGuiEditor, getExternalEditor
from .history import expandPastedTextRefs, formatPastedTextRef, getPastedTextRefNumLines
from .ide import toIDEDisplayName

EditorResult = dict[str, Any]

EDITOR_OVERRIDES = {
    "code": ["-w"],
    "subl": ["--wait"],
}


def _get_external_editor() -> str | None:
    editor = getExternalEditor()
    return str(editor) if editor else None


def isGuiEditor(editor):
    return classifyGuiEditor(str(editor or "")) is not None


def _editor_argv(editor: str, file_path: str) -> list[str]:
    argv = shlex.split(editor)
    if not argv:
        return []
    extra = EDITOR_OVERRIDES.get(argv[0].lower(), [])
    for flag in extra:
        if flag not in argv[1:]:
            argv.append(flag)
    argv.append(file_path)
    return argv


def editFileInEditor(filePath):
    editor = _get_external_editor()
    if not editor:
        return {"content": None}

    path = Path(filePath)
    if not path.exists():
        return {"content": None}

    try:
        completed = subprocess.run(_editor_argv(editor, str(path)), check=False)
        if completed.returncode != 0:
            return {
                "content": None,
                "error": f"{toIDEDisplayName(editor)} exited with code {completed.returncode}",
            }
        return {"content": path.read_text(encoding="utf-8")}
    except Exception:
        return {"content": None}


def recollapsePastedContent(editedPrompt, originalPrompt, pastedContents):
    del originalPrompt
    collapsed = editedPrompt
    for raw_id, content in (pastedContents or {}).items():
        if not isinstance(content, dict) or content.get("type") != "text":
            continue
        content_str = str(content.get("content") or "")
        content_index = collapsed.find(content_str)
        if content_index == -1:
            continue
        paste_id = int(raw_id)
        ref = formatPastedTextRef(paste_id, getPastedTextRefNumLines(content_str))
        collapsed = collapsed[:content_index] + ref + collapsed[content_index + len(content_str):]
    return collapsed


def editPromptInEditor(currentPrompt, pastedContents=None):
    temp_path: str | None = None
    try:
        expanded_prompt = (
            expandPastedTextRefs(currentPrompt, pastedContents)
            if pastedContents
            else currentPrompt
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(expanded_prompt)
            handle.flush()
            temp_path = handle.name

        result = editFileInEditor(temp_path)
        if result.get("content") is None:
            return result

        final_content = str(result["content"])
        if final_content.endswith("\n") and not final_content.endswith("\n\n"):
            final_content = final_content[:-1]
        if pastedContents:
            final_content = recollapsePastedContent(final_content, currentPrompt, pastedContents)
        return {"content": final_content}
    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass


is_gui_editor = isGuiEditor
edit_file_in_editor = editFileInEditor
recollapse_pasted_content = recollapsePastedContent
edit_prompt_in_editor = editPromptInEditor

