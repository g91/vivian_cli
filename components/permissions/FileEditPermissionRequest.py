"""File edit permission request — compact port of src/components/permissions/FileEditPermissionRequest/FileEditPermissionRequest.tsx."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ...bootstrap.state import getOriginalCwd
from ...keybindings.shortcutFormat import getShortcutDisplay
from ...state.AppState import useAppStateMaybeOutsideOfProvider
from ...utils.diff import getPatchForDisplay
from ...utils.path import expandPath, getDirectoryForPath
from ...utils.permissions.filesystem import pathInAllowedWorkingPath
from .PermissionDialog import PermissionDialog
from .PermissionPrompt import PermissionPrompt, PermissionPromptOption, ToolAnalyticsContext


def _tool_value(tool_use_confirm: Any, name: str, default: Any = None) -> Any:
    if hasattr(tool_use_confirm, name):
        return getattr(tool_use_confirm, name)
    if isinstance(tool_use_confirm, dict):
        return tool_use_confirm.get(name, default)
    return default


def _input_data(tool_use_confirm: Any) -> dict[str, Any]:
    input_data = _tool_value(tool_use_confirm, "input", {}) or {}
    return input_data if isinstance(input_data, dict) else {}


def _tool_name(tool_use_confirm: Any) -> str:
    tool = _tool_value(tool_use_confirm, "tool", {}) or {}
    if isinstance(tool, dict):
        return str(tool.get("name") or "Tool")
    return str(getattr(tool, "name", "Tool"))


def _tool_is_mcp(tool_use_confirm: Any) -> bool:
    tool = _tool_value(tool_use_confirm, "tool", {}) or {}
    if isinstance(tool, dict):
        return bool(tool.get("isMcp", False))
    return bool(getattr(tool, "isMcp", False))


def _working_paths(tool_permission_context: dict[str, Any] | None) -> list[str]:
    cwd = expandPath(getOriginalCwd())
    paths = [cwd]
    additional = (tool_permission_context or {}).get("additionalWorkingDirectories") or {}
    if isinstance(additional, dict):
        for key, value in additional.items():
            candidate = value.get("path") if isinstance(value, dict) else key
            if candidate:
                paths.append(expandPath(str(candidate)))
    return paths


def _build_write_session_suggestions(file_path: str, tool_permission_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    context = tool_permission_context or {}
    suggestions: list[dict[str, Any]] = []
    if (context.get("mode") or "default") in {"default", "plan"}:
        suggestions.append({"type": "setMode", "mode": "acceptEdits", "destination": "session"})
    absolute_path = expandPath(file_path)
    if not pathInAllowedWorkingPath(absolute_path, _working_paths(context)):
        suggestions.append(
            {"type": "addDirectories", "directories": [getDirectoryForPath(absolute_path)], "destination": "session"}
        )
    return suggestions


def _preview_lines(file_path: str, old_string: str, new_string: str, replace_all: bool) -> list[str]:
    try:
        file_contents = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        file_contents = old_string
    patch = getPatchForDisplay(
        {
            "filePath": file_path,
            "fileContents": file_contents,
            "edits": [{"old_string": old_string, "new_string": new_string, "replace_all": replace_all}],
        }
    )
    if not patch:
        return ["(No visible diff preview)"]
    lines: list[str] = []
    for hunk in patch:
        lines.append(f"@@ -{hunk['oldStart']},{hunk['oldLines']} +{hunk['newStart']},{hunk['newLines']} @@")
        lines.extend(str(line) for line in hunk.get("lines", []))
    return lines


@dataclass
class FileEditPermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None
    _prompt: PermissionPrompt[str] = field(init=False)
    _tool_permission_context: dict[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        tool_permission_context = useAppStateMaybeOutsideOfProvider(lambda state: state.get("toolPermissionContext"))
        self._tool_permission_context = tool_permission_context if isinstance(tool_permission_context, dict) else {}
        self._prompt = PermissionPrompt(
            options=[
                PermissionPromptOption(value="yes", label="Yes", feedbackConfig={"type": "accept"}),
                PermissionPromptOption(value="yes-session", label=self._session_label()),
                PermissionPromptOption(value="no", label="No", feedbackConfig={"type": "reject"}),
            ],
            onSelect=self._handle_select,
            onCancel=self._handle_cancel,
            toolAnalyticsContext=ToolAnalyticsContext(toolName=_tool_name(self.toolUseConfirm), isMcp=_tool_is_mcp(self.toolUseConfirm)),
        )

    def _parsed(self) -> dict[str, Any]:
        input_data = _input_data(self.toolUseConfirm)
        return {
            "file_path": str(input_data.get("file_path") or ""),
            "old_string": str(input_data.get("old_string") or ""),
            "new_string": str(input_data.get("new_string") or ""),
            "replace_all": bool(input_data.get("replace_all", False)),
        }

    def _session_label(self) -> str:
        file_path = self._parsed()["file_path"]
        if pathInAllowedWorkingPath(expandPath(file_path), _working_paths(self._tool_permission_context)):
            shortcut = getShortcutDisplay("chat:cycleMode", "Chat", "shift+tab")
            return f"Yes, allow all edits during this session ({shortcut})"
        dir_name = os.path.basename(getDirectoryForPath(expandPath(file_path))) or "this directory"
        shortcut = getShortcutDisplay("chat:cycleMode", "Chat", "shift+tab")
        return f"Yes, allow all edits in {dir_name}/ during this session ({shortcut})"

    def _handle_select(self, value: str, feedback: str | None = None) -> None:
        parsed = self._parsed()
        on_allow = _tool_value(self.toolUseConfirm, "onAllow")
        if value == "yes":
            if callable(on_allow):
                on_allow(parsed, [], feedback)
            self.onDone()
            return
        if value == "yes-session":
            if callable(on_allow):
                on_allow(parsed, _build_write_session_suggestions(parsed["file_path"], self._tool_permission_context))
            self.onDone()
            return
        on_reject = _tool_value(self.toolUseConfirm, "onReject")
        if callable(on_reject):
            on_reject(feedback)
        self.onReject()
        self.onDone()

    def _handle_cancel(self) -> None:
        self._handle_select("no")

    def handleKeyDown(self, event: Any) -> None:
        self._prompt.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        parsed = self._parsed()
        file_path = parsed["file_path"]
        relative_path = os.path.relpath(file_path, getOriginalCwd()) if file_path else ""
        basename = os.path.basename(file_path) if file_path else "file"
        question = f"Do you want to make this edit to {basename}?"
        children = []
        if relative_path:
            children.append(relative_path)
        children.append(question)
        children.append("")
        children.extend(_preview_lines(file_path, parsed["old_string"], parsed["new_string"], parsed["replace_all"]))
        children.append("")
        children.extend(self._prompt.render_lines())
        return PermissionDialog(title="Edit file", workerBadge=self.workerBadge, children=children).render_lines()


__all__ = ["FileEditPermissionRequest"]