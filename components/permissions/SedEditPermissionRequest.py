"""Sed edit permission request — compact port of src/components/permissions/SedEditPermissionRequest/SedEditPermissionRequest.tsx."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ...bootstrap.state import getOriginalCwd
from ...state.AppState import useAppStateMaybeOutsideOfProvider
from ...tools.BashTool.sedEditParser import SedEditInfo, applySedSubstitution
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
        suggestions.append({
            "type": "addDirectories",
            "directories": [getDirectoryForPath(absolute_path)],
            "destination": "session",
        })
    return suggestions


def _preview_lines(file_path: str, old_string: str, new_string: str) -> list[str]:
    patch = getPatchForDisplay(
        {
            "filePath": file_path,
            "fileContents": old_string,
            "edits": [{"old_string": old_string, "new_string": new_string, "replace_all": False}],
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
class SedEditPermissionRequest:
    toolUseConfirm: Any
    sedInfo: SedEditInfo
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None
    _prompt: PermissionPrompt[str] = field(init=False)
    _tool_permission_context: dict[str, Any] = field(init=False, default_factory=dict)
    _old_content: str = field(init=False, default="")
    _new_content: str = field(init=False, default="")
    _file_exists: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        tool_permission_context = useAppStateMaybeOutsideOfProvider(lambda state: state.get("toolPermissionContext"))
        self._tool_permission_context = tool_permission_context if isinstance(tool_permission_context, dict) else {}
        file_path = expandPath(self.sedInfo.filePath)
        try:
            self._old_content = Path(file_path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
            self._file_exists = True
        except OSError:
            self._old_content = ""
            self._file_exists = False
        self._new_content = applySedSubstitution(self._old_content, self.sedInfo)
        self._prompt = PermissionPrompt(
            options=[
                PermissionPromptOption(value="yes", label="Yes", feedbackConfig={"type": "accept"}),
                PermissionPromptOption(value="yes-session", label=self._session_label()),
                PermissionPromptOption(value="no", label="No", feedbackConfig={"type": "reject"}),
            ],
            onSelect=self._handle_select,
            onCancel=self._handle_cancel,
            toolAnalyticsContext=ToolAnalyticsContext(toolName="Bash", isMcp=_tool_is_mcp(self.toolUseConfirm)),
        )

    def _session_label(self) -> str:
        file_path = expandPath(self.sedInfo.filePath)
        if pathInAllowedWorkingPath(file_path, _working_paths(self._tool_permission_context)):
            return "Yes, allow all edits during this session"
        dir_name = os.path.basename(getDirectoryForPath(file_path)) or "this directory"
        return f"Yes, allow all edits in {dir_name}/ during this session"

    def _approved_input(self) -> dict[str, Any]:
        input_data = dict(_input_data(self.toolUseConfirm))
        input_data["_simulatedSedEdit"] = {
            "filePath": self.sedInfo.filePath,
            "newContent": self._new_content,
        }
        return input_data

    def _handle_select(self, value: str, feedback: str | None = None) -> None:
        on_allow = _tool_value(self.toolUseConfirm, "onAllow")
        if value == "yes":
            if callable(on_allow):
                on_allow(self._approved_input(), [], feedback)
            self.onDone()
            return
        if value == "yes-session":
            if callable(on_allow):
                on_allow(self._approved_input(), _build_write_session_suggestions(self.sedInfo.filePath, self._tool_permission_context))
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
        file_path = expandPath(self.sedInfo.filePath)
        relative_path = os.path.relpath(file_path, getOriginalCwd()) if file_path else ""
        basename = os.path.basename(file_path) if file_path else "file"
        question = f"Do you want to make this edit to {basename}?"
        no_changes_message = "File does not exist" if not self._file_exists else "Pattern did not match any content"
        children: list[str] = []
        if relative_path:
            children.append(relative_path)
        children.append(question)
        children.append("")
        if self._old_content != self._new_content:
            children.extend(_preview_lines(file_path, self._old_content, self._new_content))
        else:
            children.append(no_changes_message)
        children.append("")
        children.extend(self._prompt.render_lines())
        return PermissionDialog(title="Edit file", workerBadge=self.workerBadge, children=children).render_lines()


__all__ = ["SedEditPermissionRequest"]