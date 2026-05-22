"""Filesystem permission request — compact port of src/components/permissions/FilesystemPermissionRequest/FilesystemPermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ...bootstrap.state import getOriginalCwd
from ...constants.tools import FILE_READ_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME
from ...services.analytics.index import logEvent
from ...state.AppState import useAppStateMaybeOutsideOfProvider
from ...utils.path import expandPath, getDirectoryForPath
from ...utils.permissions.PermissionUpdate import createReadRuleSuggestion
from ...utils.permissions.filesystem import normalizeCaseForComparison, pathInAllowedWorkingPath
from .FallbackPermissionRequest import FallbackPermissionRequest
from .PermissionDialog import PermissionDialog
from .PermissionPrompt import PermissionPrompt, PermissionPromptOption, ToolAnalyticsContext


def _tool_value(tool_use_confirm: Any, name: str, default: Any = None) -> Any:
    if hasattr(tool_use_confirm, name):
        return getattr(tool_use_confirm, name)
    if isinstance(tool_use_confirm, dict):
        return tool_use_confirm.get(name, default)
    return default


def _tool_method(tool_use_confirm: Any, name: str) -> Callable[..., Any] | None:
    tool = _tool_value(tool_use_confirm, "tool", {}) or {}
    if hasattr(tool, name):
        value = getattr(tool, name)
        return value if callable(value) else None
    if isinstance(tool, dict):
        value = tool.get(name)
        return value if callable(value) else None
    return None


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


def _input_data(tool_use_confirm: Any) -> dict[str, Any]:
    input_data = _tool_value(tool_use_confirm, "input", {}) or {}
    return input_data if isinstance(input_data, dict) else {}


def _extract_path(tool_use_confirm: Any) -> str | None:
    input_data = _input_data(tool_use_confirm)
    tool_name = _tool_name(tool_use_confirm)
    if tool_name == FILE_READ_TOOL_NAME:
        return str(input_data.get("file_path") or input_data.get("path") or "") or None
    if tool_name in {GLOB_TOOL_NAME, GREP_TOOL_NAME}:
        return str(input_data.get("path") or input_data.get("directory") or input_data.get("dir") or input_data.get("folder") or "") or None
    return str(input_data.get("path") or input_data.get("file_path") or "") or None


def _render_tool_use_message(tool_use_confirm: Any) -> str:
    render_fn = _tool_method(tool_use_confirm, "renderToolUseMessage")
    input_data = _input_data(tool_use_confirm)
    if callable(render_fn):
        try:
            return str(render_fn(input_data, {"theme": None, "verbose": True}))
        except TypeError:
            return str(render_fn(input_data))

    tool_name = _tool_name(tool_use_confirm)
    if tool_name == FILE_READ_TOOL_NAME:
        from ...tools.FileReadTool.UI import renderToolUseMessage as render_file_read_message

        return render_file_read_message(input_data)
    if tool_name == GLOB_TOOL_NAME:
        from ...tools.GlobTool.UI import renderToolUseMessage as render_glob_message

        return render_glob_message(input_data)
    if tool_name == GREP_TOOL_NAME:
        from ...tools.GrepTool.UI import renderToolUseMessage as render_grep_message

        return render_grep_message(input_data)
    return str(input_data)


def _user_facing_name(tool_use_confirm: Any) -> str:
    user_facing_name_fn = _tool_method(tool_use_confirm, "userFacingName")
    input_data = _input_data(tool_use_confirm)
    if callable(user_facing_name_fn):
        try:
            user_facing_name = str(user_facing_name_fn(input_data))
        except TypeError:
            user_facing_name = str(user_facing_name_fn())
        if user_facing_name:
            return user_facing_name[:-6] if user_facing_name.endswith(" (MCP)") else user_facing_name
    return _tool_name(tool_use_confirm)


def _working_paths(tool_permission_context: dict[str, Any] | None) -> list[str]:
    cwd = expandPath(getOriginalCwd())
    if not tool_permission_context:
        return [cwd]
    additional = tool_permission_context.get("additionalWorkingDirectories") or {}
    paths = [cwd]
    if isinstance(additional, dict):
        for key, value in additional.items():
            if isinstance(value, dict):
                candidate = value.get("path")
            else:
                candidate = key
            if candidate:
                paths.append(expandPath(str(candidate)))
    elif isinstance(additional, (list, tuple, set)):
        for candidate in additional:
            if candidate:
                paths.append(expandPath(str(candidate)))
    normalized: list[str] = []
    seen: set[str] = set()
    for path in paths:
        lowered = normalizeCaseForComparison(path)
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(path)
    return normalized


def _build_session_suggestions(file_path: str, tool_permission_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    absolute_path = expandPath(file_path)
    context = tool_permission_context or {}
    outside_working_dir = not pathInAllowedWorkingPath(absolute_path, _working_paths(context))
    if outside_working_dir:
        suggestion = createReadRuleSuggestion(getDirectoryForPath(absolute_path), "session")
        return [suggestion] if suggestion is not None else []
    if (context.get("mode") or "default") in {"default", "plan"}:
        return [{"type": "setMode", "mode": "acceptEdits", "destination": "session"}]
    return []


@dataclass
class FilesystemPermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None
    _prompt: PermissionPrompt[str] = field(init=False)
    _path: str | None = field(init=False)
    _tool_permission_context: dict[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._path = _extract_path(self.toolUseConfirm)
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

    def _session_label(self) -> str:
        if not self._path:
            return "Yes, during this session"
        absolute_path = expandPath(self._path)
        if pathInAllowedWorkingPath(absolute_path, _working_paths(self._tool_permission_context)):
            return "Yes, during this session"
        dir_name = (getDirectoryForPath(absolute_path).rstrip("/").rstrip("\\").split("/")[-1].split("\\")[-1] or "this directory")
        return f"Yes, allow reading from {dir_name}/ during this session"

    def _handle_select(self, value: str, feedback: str | None = None) -> None:
        input_data = _input_data(self.toolUseConfirm)
        if value == "yes":
            on_allow = _tool_value(self.toolUseConfirm, "onAllow")
            if callable(on_allow):
                on_allow(input_data, [], feedback)
            self.onDone()
            return
        if value == "yes-session":
            logEvent("tengu_permission_mode_cycled", {"toolName": _tool_name(self.toolUseConfirm), "mode": "session"})
            on_allow = _tool_value(self.toolUseConfirm, "onAllow")
            if callable(on_allow):
                on_allow(input_data, _build_session_suggestions(self._path or "", self._tool_permission_context))
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
        if not self._path:
            FallbackPermissionRequest(toolUseConfirm=self.toolUseConfirm, onDone=self.onDone, onReject=self.onReject, workerBadge=self.workerBadge).handleKeyDown(event)
            return
        self._prompt.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        if not self._path:
            return FallbackPermissionRequest(
                toolUseConfirm=self.toolUseConfirm,
                onDone=self.onDone,
                onReject=self.onReject,
                workerBadge=self.workerBadge,
            ).render_lines()

        content = [f"{_user_facing_name(self.toolUseConfirm)}({_render_tool_use_message(self.toolUseConfirm)})", ""]
        content.extend(self._prompt.render_lines())
        return PermissionDialog(
            title="Read file",
            workerBadge=self.workerBadge,
            children=content,
        ).render_lines()


__all__ = ["FilesystemPermissionRequest"]