"""Port of src/utils/settings/applySettingsChange.ts"""
from __future__ import annotations
from typing import Dict, Any, Optional, List

from .settings import getSettingsForSource, updateSettingsForSource
from .settingsCache import resetSettingsCache


def applySettingsChange(
    source: str,
    change_fn: Any,  # Callable[[Dict[str, Any]], Dict[str, Any]]
) -> Dict[str, Any]:
    """Apply a settings change function to a source and persist. Returns new settings."""
    current = getSettingsForSource(source) or {}
    updated = change_fn(dict(current))
    updateSettingsForSource(source, updated)
    resetSettingsCache()
    return updated


def setModelForSource(source: str, model: str) -> None:
    """Set the model field in a specific settings source."""
    applySettingsChange(source, lambda s: {**s, 'model': model})


def addPermissionRuleToSource(
    source: str,
    behavior: str,
    rule: str,
) -> None:
    """Add a permission rule to a specific settings source."""
    def _apply(s: Dict[str, Any]) -> Dict[str, Any]:
        perms = dict(s.get('permissions', {}))
        rules = list(perms.get(behavior, []))
        if rule not in rules:
            rules.append(rule)
        perms[behavior] = rules
        return {**s, 'permissions': perms}
    applySettingsChange(source, _apply)


def removePermissionRuleFromSource(
    source: str,
    behavior: str,
    rule: str,
) -> bool:
    """Remove a permission rule from a specific settings source. Returns True if removed."""
    current = getSettingsForSource(source) or {}
    perms = dict(current.get('permissions', {}))
    rules = list(perms.get(behavior, []))
    if rule not in rules:
        return False
    rules.remove(rule)
    perms[behavior] = rules
    applySettingsChange(source, lambda _: {**current, 'permissions': perms})
    return True
