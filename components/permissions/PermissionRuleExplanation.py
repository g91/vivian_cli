"""Permission rule explanation — compact port of src/components/permissions/PermissionRuleExplanation.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...utils.permissions.permissionRuleParser import permissionRuleValueToString


def _reason_lines(reason: Any, toolType: str) -> list[str]:
    if not isinstance(reason, dict):
        return []
    reason_type = reason.get("type")
    if reason_type == "rule":
        rule = reason.get("rule") or {}
        rule_value = rule.get("ruleValue") or {}
        source = rule.get("source")
        lines = [
            f"Permission rule {permissionRuleValueToString(rule_value)} requires confirmation for this {toolType}.",
        ]
        if source != "policySettings":
            lines.append("/permissions to update rules")
        return lines
    if reason_type == "hook":
        hook_name = reason.get("hookName", "PermissionRequest")
        details = reason.get("reason")
        hook_source = reason.get("hookSource")
        suffix = f": {details}" if details else "."
        line = f"Hook {hook_name} requires confirmation for this {toolType}{suffix}"
        if hook_source:
            line = f"{line} [{hook_source}]"
        return [line, "/hooks to update"]
    if reason_type in {"safetyCheck", "other", "workingDir", "classifier", "mode"}:
        message = reason.get("reason")
        return [str(message)] if message else []
    return []


@dataclass(slots=True)
class PermissionRuleExplanation:
    permissionResult: Any
    toolType: str

    def render_lines(self) -> list[str]:
        decision_reason = getattr(self.permissionResult, "decisionReason", None)
        if decision_reason is None and isinstance(self.permissionResult, dict):
            decision_reason = self.permissionResult.get("decisionReason")
        return _reason_lines(decision_reason, self.toolType)


__all__ = ["PermissionRuleExplanation"]