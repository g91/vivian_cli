"""Bash permission option builder."""

from __future__ import annotations

from typing import Any, Callable

from ...components.CustomSelect.select import OptionWithDescription
from ...tools.BashTool.toolName import BASH_TOOL_NAME
from ...utils.bash.commands import extractOutputRedirections
from ...utils.permissions.bashClassifier import isClassifierPermissionsEnabled
from ...utils.permissions.permissionsLoader import shouldShowAlwaysAllowOptions
from .shellPermissionHelpers import generateShellSuggestionsLabel


def _description_already_exists(description: str, existing_descriptions: list[str]) -> bool:
    normalized = description.lower().rstrip()
    return any(existing.lower().rstrip() == normalized for existing in existing_descriptions)


def _strip_bash_redirections(command: str) -> str:
    result = extractOutputRedirections(command)
    command_without_redirections = str(result.get("commandWithoutRedirections") or command)
    redirections = result.get("redirections") or []
    return command_without_redirections if len(redirections) > 0 else command


def bashToolUseOptions(
    *,
    suggestions: list[dict[str, Any]] | None = None,
    decisionReason: dict[str, Any] | None = None,
    onRejectFeedbackChange: Callable[[str], None],
    onAcceptFeedbackChange: Callable[[str], None],
    onClassifierDescriptionChange: Callable[[str], None] | None = None,
    classifierDescription: str | None = None,
    initialClassifierDescriptionEmpty: bool = False,
    existingAllowDescriptions: list[str] | None = None,
    yesInputMode: bool = False,
    noInputMode: bool = False,
    editablePrefix: str | None = None,
    onEditablePrefixChange: Callable[[str], None] | None = None,
) -> list[OptionWithDescription[str]]:
    suggestions = suggestions or []
    existing_allow_descriptions = existingAllowDescriptions or []
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

    if shouldShowAlwaysAllowOptions():
        has_non_bash_suggestions = any(
            suggestion.get("type") == "addDirectories"
            or (
                suggestion.get("type") == "addRules"
                and any(
                    isinstance(rule, dict) and rule.get("toolName") != BASH_TOOL_NAME
                    for rule in suggestion.get("rules", []) or []
                )
            )
            for suggestion in suggestions
        )
        if (
            editablePrefix is not None
            and onEditablePrefixChange is not None
            and not has_non_bash_suggestions
            and len(suggestions) > 0
        ):
            options.append(
                OptionWithDescription(
                    type="input",
                    label="Yes, and don't ask again for",
                    value="yes-prefix-edited",
                    placeholder="command prefix (e.g., npm run:*)",
                    initialValue=editablePrefix,
                    onChange=onEditablePrefixChange,
                    allowEmptySubmitToCancel=True,
                    showLabelWithValue=True,
                    labelValueSeparator=": ",
                    resetCursorOnUpdate=True,
                )
            )
        elif len(suggestions) > 0:
            label = generateShellSuggestionsLabel(suggestions, BASH_TOOL_NAME, _strip_bash_redirections)
            if label:
                options.append(OptionWithDescription(label=label, value="yes-apply-suggestions"))

        editable_prefix_shown = any(option.value == "yes-prefix-edited" for option in options)
        if (
            not editable_prefix_shown
            and isClassifierPermissionsEnabled()
            and onClassifierDescriptionChange is not None
            and not initialClassifierDescriptionEmpty
            and not _description_already_exists(classifierDescription or "", existing_allow_descriptions)
            and (decisionReason or {}).get("type") != "classifier"
        ):
            options.append(
                OptionWithDescription(
                    type="input",
                    label="Yes, and don't ask again for",
                    value="yes-classifier-reviewed",
                    placeholder="describe what to allow...",
                    initialValue=classifierDescription or "",
                    onChange=onClassifierDescriptionChange,
                    allowEmptySubmitToCancel=True,
                    showLabelWithValue=True,
                    labelValueSeparator=": ",
                    resetCursorOnUpdate=True,
                )
            )

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


__all__ = ["bashToolUseOptions"]