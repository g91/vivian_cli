"""Web fetch permission request — focused port of src/components/permissions/WebFetchPermissionRequest/WebFetchPermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from urllib.parse import urlparse

from ...tools.WebFetchTool.UI import renderToolUseMessage
from ...utils.permissions.permissionsLoader import shouldShowAlwaysAllowOptions
from ..CustomSelect import OptionWithDescription, Select
from .PermissionDialog import PermissionDialog
from .PermissionRuleExplanation import PermissionRuleExplanation


WebFetchPermissionSelection = Literal["yes", "yes-dont-ask-again-domain", "no"]


def inputToPermissionRuleContent(input_data: dict[str, Any]) -> str:
    try:
        url = str((input_data or {}).get("url") or "")
        hostname = urlparse(url).hostname
        if hostname:
            return f"domain:{hostname}"
    except Exception:
        return f"input:{input_data}"
    return f"input:{input_data}"


@dataclass
class WebFetchPermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    verbose: bool = False
    workerBadge: Any = None
    select: Select[WebFetchPermissionSelection] = field(init=False)

    def __post_init__(self) -> None:
        input_data = self._tool_value("input", {}) or {}
        url = str(input_data.get("url") or "")
        hostname = urlparse(url).hostname or url
        options: list[OptionWithDescription[WebFetchPermissionSelection]] = [
            OptionWithDescription(label="Yes", value="yes"),
        ]
        if shouldShowAlwaysAllowOptions():
            options.append(
                OptionWithDescription(
                    label=f"Yes, and don't ask again for {hostname}",
                    value="yes-dont-ask-again-domain",
                )
            )
        options.append(
            OptionWithDescription(
                label="No, and tell vivian what to do differently (esc)",
                value="no",
            )
        )
        self.select = Select(options=options, onChange=self._handle_change, onCancel=self._handle_cancel)

    def _tool_value(self, name: str, default: Any = None) -> Any:
        if hasattr(self.toolUseConfirm, name):
            return getattr(self.toolUseConfirm, name)
        if isinstance(self.toolUseConfirm, dict):
            return self.toolUseConfirm.get(name, default)
        return default

    def _handle_change(self, value: WebFetchPermissionSelection) -> None:
        input_data = self._tool_value("input", {}) or {}
        on_allow = self._tool_value("onAllow")
        if value == "yes":
            if callable(on_allow):
                on_allow(input_data, [])
            self.onDone()
            return
        if value == "yes-dont-ask-again-domain":
            tool = self._tool_value("tool", {}) or {}
            tool_name = getattr(tool, "name", None)
            if tool_name is None and isinstance(tool, dict):
                tool_name = tool.get("name")
            rule_value = {
                "toolName": str(tool_name or "WebFetch"),
                "ruleContent": inputToPermissionRuleContent(input_data),
            }
            if callable(on_allow):
                on_allow(
                    input_data,
                    [{
                        "type": "addRules",
                        "rules": [rule_value],
                        "behavior": "allow",
                        "destination": "localSettings",
                    }],
                )
            self.onDone()
            return
        on_reject = self._tool_value("onReject")
        if callable(on_reject):
            on_reject()
        self.onReject()
        self.onDone()

    def _handle_cancel(self) -> None:
        self._handle_change("no")

    def handleKeyDown(self, event: object) -> None:
        self.select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        input_data = self._tool_value("input", {}) or {}
        description = self._tool_value("description")
        permission_result = self._tool_value("permissionResult")
        header_lines: list[str] = []
        tool_use_message = renderToolUseMessage(input_data, {"verbose": self.verbose})
        if tool_use_message:
            header_lines.append(tool_use_message)
        if description:
            header_lines.append(str(description))
        children = list(header_lines)
        explanation_lines = PermissionRuleExplanation(
            permissionResult=permission_result,
            toolType="tool",
        ).render_lines()
        if explanation_lines:
            children.append("")
            children.extend(explanation_lines)
        children.append("")
        children.append("Do you want to allow vivian to fetch this content?")
        children.extend(self.select.render_lines())
        return PermissionDialog(title="Fetch", children=children, workerBadge=self.workerBadge).render_lines()


__all__ = ["WebFetchPermissionRequest", "WebFetchPermissionSelection", "inputToPermissionRuleContent"]