"""PowerShell permission option builder."""

from __future__ import annotations

from typing import Any, Callable

from ...components.CustomSelect.select import OptionWithDescription
from ...tools.PowerShellTool.toolName import POWERSHELL_TOOL_NAME
from ...utils.permissions.permissionsLoader import shouldShowAlwaysAllowOptions
from .shellPermissionHelpers import generateShellSuggestionsLabel


def powershellToolUseOptions(
    *,
    suggestions: list[dict[str, Any]] | None = None,
    onRejectFeedbackChange: Callable[[str], None],
    onAcceptFeedbackChange: Callable[[str], None],
    yesInputMode: bool = False,
    noInputMode: bool = False,
    editablePrefix: str | None = None,
    onEditablePrefixChange: Callable[[str], None] | None = None,
) -> list[OptionWithDescription[str]]:
    suggestions = suggestions or []
    options: list[OptionWithDescription[str]] = []
    if yesInputMode:
        options.append(
            OptionWithDescription(
                type="input",
                label="Yes",
                value="yes",
                placeholder="and tell vivian what to do next",
                onChange=onAcceptFeedbackChange,
                allowEmptySubmitToCancel=True,
            )
        )
    else:
        options.append(OptionWithDescription(label="Yes", value="yes"))

    if shouldShowAlwaysAllowOptions() and suggestions:
        has_non_powershell_suggestions = any(
            suggestion.get("type") == "addDirectories"
            or (
                suggestion.get("type") == "addRules"
                and any(
                    isinstance(rule, dict) and rule.get("toolName") != POWERSHELL_TOOL_NAME
                    for rule in suggestion.get("rules", []) or []
                )
            )
            for suggestion in suggestions
        )
        if editablePrefix is not None and onEditablePrefixChange is not None and not has_non_powershell_suggestions:
            options.append(
                OptionWithDescription(
                    type="input",
                    label="Yes, and don't ask again for",
                    value="yes-prefix-edited",
                    placeholder="command prefix (e.g., Get-Process:*)",
                    initialValue=editablePrefix,
                    onChange=onEditablePrefixChange,
                    allowEmptySubmitToCancel=True,
                    showLabelWithValue=True,
                    labelValueSeparator=": ",
                    resetCursorOnUpdate=True,
                )
            )
        else:
            label = generateShellSuggestionsLabel(suggestions, POWERSHELL_TOOL_NAME)
            if label:
                options.append(OptionWithDescription(label=label, value="yes-apply-suggestions"))

    if noInputMode:
        options.append(
            OptionWithDescription(
                type="input",
                label="No",
                value="no",
                placeholder="and tell vivian what to do differently",
                onChange=onRejectFeedbackChange,
                allowEmptySubmitToCancel=True,
            )
        )
    else:
        options.append(OptionWithDescription(label="No", value="no"))
    return options


__all__ = ["powershellToolUseOptions"]