"""Permission request dispatcher — compact port of src/components/permissions/PermissionRequest.tsx."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from ...constants.tools import (
    ASK_USER_QUESTION_TOOL_NAME,
    BASH_TOOL_NAME,
    ENTER_PLAN_MODE_TOOL_NAME,
    EXIT_PLAN_MODE_TOOL_NAME,
    FILE_EDIT_TOOL_NAME,
    FILE_READ_TOOL_NAME,
    FILE_WRITE_TOOL_NAME,
    GLOB_TOOL_NAME,
    GREP_TOOL_NAME,
    NOTEBOOK_EDIT_TOOL_NAME,
    POWERSHELL_TOOL_NAME,
    SKILL_TOOL_NAME,
    WEB_FETCH_TOOL_NAME,
)
from .AskUserQuestionPermissionRequest import AskUserQuestionPermissionRequest
from .BashPermissionRequest import BashPermissionRequest
from .EnterPlanModePermissionRequest import EnterPlanModePermissionRequest
from .ExitPlanModePermissionRequest import ExitPlanModePermissionRequest
from .FallbackPermissionRequest import FallbackPermissionRequest
from .FileEditPermissionRequest import FileEditPermissionRequest
from .FilesystemPermissionRequest import FilesystemPermissionRequest
from .FileWritePermissionRequest import FileWritePermissionRequest
from .NotebookEditPermissionRequest import NotebookEditPermissionRequest
from .PowerShellPermissionRequest import PowerShellPermissionRequest
from .SkillPermissionRequest import SkillPermissionRequest
from .WebFetchPermissionRequest import WebFetchPermissionRequest


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name") or "")
    return str(getattr(tool, "name", "") or "")


def permissionComponentForTool(tool: Any) -> type[Any]:
    tool_name = _tool_name(tool)
    if tool_name == FILE_EDIT_TOOL_NAME:
        return FileEditPermissionRequest
    if tool_name == FILE_WRITE_TOOL_NAME:
        return FileWritePermissionRequest
    if tool_name == BASH_TOOL_NAME:
        return BashPermissionRequest
    if tool_name == POWERSHELL_TOOL_NAME:
        return PowerShellPermissionRequest
    if tool_name == WEB_FETCH_TOOL_NAME:
        return WebFetchPermissionRequest
    if tool_name == NOTEBOOK_EDIT_TOOL_NAME:
        return NotebookEditPermissionRequest
    if tool_name == EXIT_PLAN_MODE_TOOL_NAME:
        return ExitPlanModePermissionRequest
    if tool_name == ENTER_PLAN_MODE_TOOL_NAME:
        return EnterPlanModePermissionRequest
    if tool_name == SKILL_TOOL_NAME:
        return SkillPermissionRequest
    if tool_name == ASK_USER_QUESTION_TOOL_NAME:
        return AskUserQuestionPermissionRequest
    if tool_name in {GLOB_TOOL_NAME, GREP_TOOL_NAME, FILE_READ_TOOL_NAME}:
        return FilesystemPermissionRequest
    return FallbackPermissionRequest


def permission_component_for_tool(tool: Any) -> type[Any]:
    return permissionComponentForTool(tool)


@dataclass
class PermissionRequest:
    toolUseConfirm: Any
    toolUseContext: Any = None
    onDone: Callable[[], None] = lambda: None
    onReject: Callable[[], None] = lambda: None
    verbose: bool = False
    workerBadge: Any = None
    setStickyFooter: Callable[[Any], None] | None = None
    _component: Any = field(init=False)

    def __post_init__(self) -> None:
        component_cls = permissionComponentForTool(self._tool_value("tool"))
        kwargs = {
            "toolUseConfirm": self.toolUseConfirm,
            "toolUseContext": self.toolUseContext,
            "onDone": self.onDone,
            "onReject": self.onReject,
            "verbose": self.verbose,
            "workerBadge": self.workerBadge,
            "setStickyFooter": self.setStickyFooter,
        }
        signature = inspect.signature(component_cls)
        accepted = {name: value for name, value in kwargs.items() if name in signature.parameters}
        self._component = component_cls(**accepted)

    def _tool_value(self, name: str, default: Any = None) -> Any:
        if hasattr(self.toolUseConfirm, name):
            return getattr(self.toolUseConfirm, name)
        if isinstance(self.toolUseConfirm, dict):
            return self.toolUseConfirm.get(name, default)
        return default

    def handleKeyDown(self, event: Any) -> None:
        handler = getattr(self._component, "handleKeyDown", None)
        if callable(handler):
            handler(event)

    def render_lines(self) -> list[str]:
        renderer = getattr(self._component, "render_lines", None)
        if callable(renderer):
            return renderer()
        return [str(self._component)]


__all__ = ["PermissionRequest", "permissionComponentForTool", "permission_component_for_tool"]