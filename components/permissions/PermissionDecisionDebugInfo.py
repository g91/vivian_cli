"""Compact permission decision debug info."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...constants.figures import BULLET_OPERATOR
from ...state.AppState import useAppStateMaybeOutsideOfProvider
from ...utils.permissions.PermissionMode import permissionModeTitle
from ...utils.permissions.permissions import getAllowRules, getAskRules, getDenyRules
from ...utils.permissions.permissionRuleParser import permissionRuleValueToString
from ...utils.permissions.shadowedRuleDetection import detectUnreachableRules
from ...utils.sandbox.sandbox_adapter import SandboxManager
from ...utils.settings.constants import getSettingSourceDisplayNameLowercase


def _extract_rules(updates: Any) -> list[dict[str, Any]]:
    if not isinstance(updates, list):
        return []
    rules: list[dict[str, Any]] = []
    for update in updates:
        if isinstance(update, dict) and update.get("type") == "addRules":
            for rule in update.get("rules", []) or []:
                if isinstance(rule, dict):
                    rules.append(rule)
    return rules


def _extract_directories(updates: Any) -> list[str]:
    if not isinstance(updates, list):
        return []
    directories: list[str] = []
    for update in updates:
        if isinstance(update, dict) and update.get("type") == "addDirectories":
            directories.extend(str(directory) for directory in update.get("directories", []) or [])
    return directories


def _extract_mode(updates: Any) -> str | None:
    if not isinstance(updates, list):
        return None
    for update in reversed(updates):
        if isinstance(update, dict) and update.get("type") == "setMode":
            mode = update.get("mode")
            return str(mode) if mode else None
    return None


def _decision_reason_display_string(decision_reason: Any) -> str:
    if not isinstance(decision_reason, dict):
        return ""
    reason_type = decision_reason.get("type")
    if reason_type == "classifier":
        classifier = decision_reason.get("classifier")
        reason = decision_reason.get("reason")
        return f"{classifier} classifier: {reason}" if classifier and reason else str(reason or "")
    if reason_type == "rule":
        rule = decision_reason.get("rule") or {}
        rule_value = rule.get("ruleValue") or {}
        source = rule.get("source")
        return f"{permissionRuleValueToString(rule_value)} rule from {getSettingSourceDisplayNameLowercase(str(source or 'session'))}"
    if reason_type == "mode":
        return f"{permissionModeTitle(str(decision_reason.get('mode') or 'default'))} mode"
    if reason_type == "sandboxOverride":
        return "Requires permission to bypass sandbox"
    if reason_type in {"workingDir", "safetyCheck", "other", "asyncAgent"}:
        return str(decision_reason.get("reason") or "")
    if reason_type == "permissionPromptTool":
        return f"{decision_reason.get('permissionPromptToolName')} permission prompt tool"
    if reason_type == "hook":
        hook_name = decision_reason.get("hookName")
        reason = decision_reason.get("reason")
        return f"{hook_name} hook: {reason}" if reason else f"{hook_name} hook"
    return ""


def _decision_reason_lines(decision_reason: Any) -> list[str]:
    if not isinstance(decision_reason, dict):
        return ["undefined"]
    if decision_reason.get("type") != "subcommandResults":
        display = _decision_reason_display_string(decision_reason)
        return [display or "undefined"]
    reasons = decision_reason.get("reasons")
    if isinstance(reasons, dict):
        items = reasons.items()
    elif isinstance(reasons, list):
        items = reasons
    else:
        items = []
    lines: list[str] = []
    for item in items:
        if isinstance(item, tuple) and len(item) == 2:
            subcommand, result = item
        elif isinstance(item, list) and len(item) == 2:
            subcommand, result = item
        else:
            continue
        icon = "OK" if isinstance(result, dict) and result.get("behavior") == "allow" else "X"
        lines.append(f"{icon} {subcommand}")
        if isinstance(result, dict):
            sub_reason = result.get("decisionReason")
            if isinstance(sub_reason, dict) and sub_reason.get("type") != "subcommandResults":
                lines.append(f"  -> {_decision_reason_display_string(sub_reason)}")
            if result.get("behavior") == "ask":
                suggested_rules = _extract_rules(result.get("suggestions"))
                if suggested_rules:
                    rendered = ", ".join(permissionRuleValueToString(rule) for rule in suggested_rules)
                    lines.append(f"  -> Suggested rules: {rendered}")
    return lines or ["undefined"]


def _suggestion_lines(suggestions: Any, width: int = 10) -> list[str]:
    label = "Suggestions".rjust(width)
    if not isinstance(suggestions, list) or not suggestions:
        return [f"{label} None"]
    rules = _extract_rules(suggestions)
    directories = _extract_directories(suggestions)
    mode = _extract_mode(suggestions)
    if not rules and not directories and not mode:
        return [f"{label} None"]
    lines = [f"{label} "]
    if rules:
        lines.append(f"{'Rules'.rjust(width)} ")
        lines.extend(f"  {BULLET_OPERATOR} {permissionRuleValueToString(rule)}" for rule in rules)
    if directories:
        lines.append(f"{'Directories'.rjust(width)} ")
        lines.extend(f"  {BULLET_OPERATOR} {directory}" for directory in directories)
    if mode:
        lines.append(f"{'Mode'.rjust(width)} {permissionModeTitle(mode)}")
    return lines


def _tool_permission_context() -> dict[str, Any]:
    context = useAppStateMaybeOutsideOfProvider(lambda state: state.get("toolPermissionContext"))
    return dict(context or {}) if isinstance(context, dict) else {}


@dataclass(slots=True)
class PermissionDecisionDebugInfo:
    permissionResult: Any
    toolName: str | None = None

    def _unreachable_rules(self, suggestions: Any) -> list[dict[str, Any]]:
        context = _tool_permission_context()
        sandbox_auto_allow = SandboxManager.isSandboxingEnabled() and SandboxManager.isAutoAllowBashIfSandboxedEnabled()
        all_rules = detectUnreachableRules(
            getAllowRules(context),
            getAskRules(context),
            getDenyRules(context),
            {"sandboxAutoAllowEnabled": sandbox_auto_allow},
        )
        suggested_rules = _extract_rules(suggestions)
        if suggested_rules:
            return [
                item
                for item in all_rules
                if any(
                    suggested.get("toolName") == item.get("rule", {}).get("ruleValue", {}).get("toolName")
                    and suggested.get("ruleContent") == item.get("rule", {}).get("ruleValue", {}).get("ruleContent")
                    for suggested in suggested_rules
                )
            ]
        if self.toolName:
            return [
                item
                for item in all_rules
                if item.get("rule", {}).get("ruleValue", {}).get("toolName") == self.toolName
            ]
        return all_rules

    def render_lines(self) -> list[str]:
        permission_result = self.permissionResult if isinstance(self.permissionResult, dict) else {}
        decision_reason = permission_result.get("decisionReason")
        suggestions = permission_result.get("suggestions") if "suggestions" in permission_result else None
        behavior = permission_result.get("behavior")
        lines = [f"{'Behavior'.rjust(10)} {behavior}"]
        if behavior != "allow":
            lines.append(f"{'Message'.rjust(10)} {permission_result.get('message')}")
        reason_lines = _decision_reason_lines(decision_reason)
        if reason_lines:
            lines.append(f"{'Reason'.rjust(10)} {reason_lines[0]}")
            lines.extend(f"{' '.rjust(10)} {line}" for line in reason_lines[1:])
        lines.extend(_suggestion_lines(suggestions, width=10))
        unreachable_rules = self._unreachable_rules(suggestions)
        if unreachable_rules:
            lines.append("")
            lines.append(f"Unreachable Rules ({len(unreachable_rules)})")
            for item in unreachable_rules:
                rule_value = item.get("rule", {}).get("ruleValue", {})
                lines.append(f"  {permissionRuleValueToString(rule_value)}")
                lines.append(f"    {item.get('reason')}")
                lines.append(f"    Fix: {item.get('fix')}")
        return lines


__all__ = ["PermissionDecisionDebugInfo"]