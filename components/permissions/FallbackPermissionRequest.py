"""Fallback permission request — compact port of src/components/permissions/FallbackPermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ...bootstrap.state import getOriginalCwd
from ...services.analytics.index import logEvent
from ...utils.env import env
from ...utils.permissions.permissionsLoader import shouldShowAlwaysAllowOptions
from .PermissionDialog import PermissionDialog
from .PermissionPrompt import PermissionPrompt, PermissionPromptOption, ToolAnalyticsContext
from .PermissionRuleExplanation import PermissionRuleExplanation


def _sanitize_tool_name_for_analytics(name: Any) -> str:
    return str(name or "unknown")


def _truncate_to_lines(value: Any, limit: int) -> str:
    text = str(value or "")
    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    return "\n".join(lines[:limit])


def _log_unary_event(event_name: str, tool_use_confirm: Any) -> None:
    assistant_message = getattr(tool_use_confirm, "assistantMessage", None)
    message = getattr(assistant_message, "message", None)
    message_id = getattr(message, "id", None)
    if message_id is None and isinstance(tool_use_confirm, dict):
        assistant_message = tool_use_confirm.get("assistantMessage") or {}
        message = assistant_message.get("message") if isinstance(assistant_message, dict) else None
        if isinstance(message, dict):
            message_id = message.get("id")
    logEvent(
        "tengu_unary_event",
        {
            "event": event_name,
            "completion_type": "tool_use_single",
            "language_name": "none",
            "message_id": message_id,
            "platform": env.platform,
        },
    )


@dataclass
class FallbackPermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None

    def __post_init__(self) -> None:
        self._prompt = PermissionPrompt(
            options=self._options(),
            onSelect=self._handle_select,
            onCancel=self._handle_cancel,
            toolAnalyticsContext=self._tool_analytics_context(),
        )

    def _tool_value(self, name: str, default: Any = None) -> Any:
        if hasattr(self.toolUseConfirm, name):
            return getattr(self.toolUseConfirm, name)
        if isinstance(self.toolUseConfirm, dict):
            return self.toolUseConfirm.get(name, default)
        return default

    def _tool_method(self, name: str, default: Callable[..., Any] | None = None) -> Callable[..., Any] | None:
        tool = self._tool_value("tool", {}) or {}
        if hasattr(tool, name):
            return getattr(tool, name)
        if isinstance(tool, dict):
            value = tool.get(name)
            return value if callable(value) else default
        return default

    def _tool_name(self) -> str:
        tool = self._tool_value("tool", {}) or {}
        if isinstance(tool, dict):
            return str(tool.get("name") or "Tool")
        return str(getattr(tool, "name", "Tool"))

    def _tool_is_mcp(self) -> bool:
        tool = self._tool_value("tool", {}) or {}
        if isinstance(tool, dict):
            return bool(tool.get("isMcp", False))
        return bool(getattr(tool, "isMcp", False))

    def _tool_analytics_context(self) -> ToolAnalyticsContext:
        return ToolAnalyticsContext(
            toolName=_sanitize_tool_name_for_analytics(self._tool_name()),
            isMcp=self._tool_is_mcp(),
        )

    def _handle_select(self, value: str, feedback: str | None = None) -> None:
        input_data = self._tool_value("input", {}) or {}
        if value == "yes":
            _log_unary_event("accept", self.toolUseConfirm)
            on_allow = self._tool_value("onAllow")
            if callable(on_allow):
                on_allow(input_data, [], feedback)
            self.onDone()
            return
        if value == "yes-dont-ask-again":
            _log_unary_event("accept", self.toolUseConfirm)
            on_allow = self._tool_value("onAllow")
            tool = self._tool_value("tool", {}) or {}
            tool_name = getattr(tool, "name", None)
            if tool_name is None and isinstance(tool, dict):
                tool_name = tool.get("name")
            if callable(on_allow):
                on_allow(
                    input_data,
                    [{
                        "type": "addRules",
                        "rules": [{"toolName": str(tool_name or "unknown")}],
                        "behavior": "allow",
                        "destination": "localSettings",
                    }],
                )
            self.onDone()
            return
        _log_unary_event("reject", self.toolUseConfirm)
        on_reject = self._tool_value("onReject")
        if callable(on_reject):
            on_reject(feedback)
        self.onReject()
        self.onDone()

    def _handle_cancel(self) -> None:
        _log_unary_event("reject", self.toolUseConfirm)
        on_reject = self._tool_value("onReject")
        if callable(on_reject):
            on_reject()
        self.onReject()
        self.onDone()

    def _options(self) -> list[PermissionPromptOption[str]]:
        user_facing_name_fn = self._tool_method("userFacingName")
        input_data = self._tool_value("input", {}) or {}
        original_user_facing_name = (
            str(user_facing_name_fn(input_data)) if callable(user_facing_name_fn) else self._tool_name()
        )
        user_facing_name = original_user_facing_name[:-6] if original_user_facing_name.endswith(" (MCP)") else original_user_facing_name
        options = [
            PermissionPromptOption(value="yes", label="Yes", feedbackConfig={"type": "accept"}),
        ]
        if shouldShowAlwaysAllowOptions():
            options.append(
                PermissionPromptOption(
                    value="yes-dont-ask-again",
                    label=f"Yes, and don't ask again for {user_facing_name} commands in {getOriginalCwd()}",
                )
            )
        options.append(PermissionPromptOption(value="no", label="No", feedbackConfig={"type": "reject"}))
        return options

    def render_lines(self) -> list[str]:
        input_data = self._tool_value("input", {}) or {}
        description = _truncate_to_lines(self._tool_value("description", ""), 3)
        user_facing_name_fn = self._tool_method("userFacingName")
        render_tool_use_message_fn = self._tool_method("renderToolUseMessage")
        original_user_facing_name = (
            str(user_facing_name_fn(input_data)) if callable(user_facing_name_fn) else self._tool_name()
        )
        user_facing_name = original_user_facing_name[:-6] if original_user_facing_name.endswith(" (MCP)") else original_user_facing_name
        mcp_suffix = " (MCP)" if original_user_facing_name.endswith(" (MCP)") else ""
        tool_message = (
            str(render_tool_use_message_fn(input_data, {"theme": None, "verbose": True}))
            if callable(render_tool_use_message_fn)
            else str(input_data)
        )
        lines = [f"{user_facing_name}({tool_message}){mcp_suffix}"]
        if description:
            lines.append(description)
        explanation_lines = PermissionRuleExplanation(permissionResult=self._tool_value("permissionResult"), toolType="tool").render_lines()
        if explanation_lines:
            lines.append("")
            lines.extend(explanation_lines)
        lines.append("")
        lines.extend(self._prompt.render_lines())
        return PermissionDialog(title="Permission required", children=lines, workerBadge=self.workerBadge).render_lines()

    def handleKeyDown(self, event: Any) -> None:
        self._prompt.handleKeyDown(event)


__all__ = ["FallbackPermissionRequest"]