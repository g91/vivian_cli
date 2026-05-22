"""Skill permission request — compact port of src/components/permissions/SkillPermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ...bootstrap.state import getOriginalCwd
from ...services.analytics.index import logEvent
from ...tools.SkillTool.constants import SKILL_TOOL_NAME
from ...utils.env import env
from ...utils.log import logError
from ...utils.permissions.permissionsLoader import shouldShowAlwaysAllowOptions
from .PermissionDialog import PermissionDialog
from .PermissionPrompt import PermissionPrompt, PermissionPromptOption, ToolAnalyticsContext
from .PermissionRuleExplanation import PermissionRuleExplanation


def _sanitize_tool_name_for_analytics(name: Any) -> str:
    return str(name or "unknown")


def _message_id(tool_use_confirm: Any) -> Any:
    assistant_message = getattr(tool_use_confirm, "assistantMessage", None)
    message = getattr(assistant_message, "message", None)
    message_id = getattr(message, "id", None)
    if message_id is None and isinstance(tool_use_confirm, dict):
        assistant_message = tool_use_confirm.get("assistantMessage") or {}
        message = assistant_message.get("message") if isinstance(assistant_message, dict) else None
        if isinstance(message, dict):
            message_id = message.get("id")
    return message_id


def _log_unary_event(event_name: str, tool_use_confirm: Any) -> None:
    logEvent(
        "tengu_unary_event",
        {
            "event": event_name,
            "completion_type": "tool_use_single",
            "language_name": "none",
            "message_id": _message_id(tool_use_confirm),
            "platform": env.platform,
        },
    )


@dataclass
class SkillPermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None

    def __post_init__(self) -> None:
        self.skill = self._parse_input(self._tool_value("input", {}))
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

    def _permission_result(self) -> Any:
        return self._tool_value("permissionResult", {}) or {}

    def _command_obj(self) -> Any:
        permission_result = self._permission_result()
        if not isinstance(permission_result, dict):
            behavior = getattr(permission_result, "behavior", None)
            metadata = getattr(permission_result, "metadata", None)
        else:
            behavior = permission_result.get("behavior")
            metadata = permission_result.get("metadata")
        if behavior != "ask" or not metadata:
            return None
        if isinstance(metadata, dict):
            return metadata.get("command")
        return getattr(metadata, "command", None)

    def _parse_input(self, input_data: Any) -> str:
        if isinstance(input_data, dict):
            skill = input_data.get("skill") or input_data.get("skill_name")
            arguments = input_data.get("arguments")
        else:
            skill = getattr(input_data, "skill", None) or getattr(input_data, "skill_name", None)
            arguments = getattr(input_data, "arguments", None)
        if not skill:
            logError(Exception("Failed to parse skill tool input: missing skill"))
            return ""
        skill_text = str(skill)
        if arguments in (None, {}, [], ""):
            return skill_text
        return f"{skill_text} {arguments}"

    def _options(self) -> list[PermissionPromptOption[str]]:
        options: list[PermissionPromptOption[str]] = [
            PermissionPromptOption(value="yes", label="Yes", feedbackConfig={"type": "accept"}),
        ]
        if shouldShowAlwaysAllowOptions():
            options.append(
                PermissionPromptOption(
                    value="yes-exact",
                    label=f"Yes, and don't ask again for {self.skill} in {getOriginalCwd()}",
                )
            )
            space_index = self.skill.find(" ")
            if space_index > 0:
                command_prefix = self.skill[:space_index]
                options.append(
                    PermissionPromptOption(
                        value="yes-prefix",
                        label=f"Yes, and don't ask again for {command_prefix}:* commands in {getOriginalCwd()}",
                    )
                )
        options.append(PermissionPromptOption(value="no", label="No", feedbackConfig={"type": "reject"}))
        return options

    def _handle_select(self, value: str, feedback: str | None = None) -> None:
        input_data = self._tool_value("input", {}) or {}
        if value == "yes":
            _log_unary_event("accept", self.toolUseConfirm)
            on_allow = self._tool_value("onAllow")
            if callable(on_allow):
                on_allow(input_data, [], feedback)
            self.onDone()
            return
        if value == "yes-exact":
            _log_unary_event("accept", self.toolUseConfirm)
            on_allow = self._tool_value("onAllow")
            if callable(on_allow):
                on_allow(
                    input_data,
                    [{
                        "type": "addRules",
                        "rules": [{"toolName": SKILL_TOOL_NAME, "ruleContent": self.skill}],
                        "behavior": "allow",
                        "destination": "localSettings",
                    }],
                )
            self.onDone()
            return
        if value == "yes-prefix":
            _log_unary_event("accept", self.toolUseConfirm)
            space_index = self.skill.find(" ")
            command_prefix = self.skill[:space_index] if space_index > 0 else self.skill
            on_allow = self._tool_value("onAllow")
            if callable(on_allow):
                on_allow(
                    input_data,
                    [{
                        "type": "addRules",
                        "rules": [{"toolName": SKILL_TOOL_NAME, "ruleContent": f"{command_prefix}:*"}],
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

    def render_lines(self) -> list[str]:
        lines = ["vivian may use instructions, code, or files from this Skill."]
        command_obj = self._command_obj()
        description = None
        if isinstance(command_obj, dict):
            description = command_obj.get("description")
        elif command_obj is not None:
            description = getattr(command_obj, "description", None)
        if description:
            lines.append("")
            lines.append(str(description))
        explanation = PermissionRuleExplanation(permissionResult=self._permission_result(), toolType="tool").render_lines()
        if explanation:
            lines.append("")
            lines.extend(explanation)
        lines.append("")
        lines.extend(self._prompt.render_lines())
        return PermissionDialog(title=f'Use skill "{self.skill}"?', workerBadge=self.workerBadge, children=lines).render_lines()

    def handleKeyDown(self, event: Any) -> None:
        self._prompt.handleKeyDown(event)


__all__ = ["SkillPermissionRequest"]