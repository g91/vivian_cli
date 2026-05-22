"""Port of src/utils/settings/validation.ts"""
from __future__ import annotations
import json
from typing import Optional, List, Dict, Any, Tuple


class ValidationError(Exception):
    """Raised when settings or permission rule validation fails."""
    def __init__(self, field: str, message: str, value: Any = None):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message
        self.value = value


def formatValidationError(error: Dict[str, Any]) -> str:
    """Format a validation error dict as a human-readable string."""
    path = error.get('path', [])
    msg = error.get('message', 'Invalid value')
    if path:
        return f"{'.'.join(str(p) for p in path)}: {msg}"
    return msg


def formatValidationErrors(errors: List[Dict[str, Any]]) -> str:
    """Format a list of validation errors as a human-readable string."""
    return '; '.join(formatValidationError(e) for e in errors)


VALID_PERMISSION_BEHAVIORS = {'allow', 'deny', 'ask'}
VALID_THEMES = {'light', 'dark', 'auto'}
VALID_NOTIF_CHANNELS = {'terminal', 'iterm', 'osc', 'none'}


def validatePermissionRuleString(rule_str: str) -> Optional[str]:
    """Validate a single permission rule string. Returns error message or None."""
    if not isinstance(rule_str, str):
        return 'Permission rule must be a string'
    rule_str = rule_str.strip()
    if not rule_str:
        return 'Permission rule cannot be empty'
    if len(rule_str) > 4096:
        return 'Permission rule is too long (max 4096 characters)'
    return None


def filterInvalidPermissionRules(rules: List[str]) -> Tuple[List[str], List[str]]:
    """Split a list into (valid_rules, invalid_rules)."""
    valid = []
    invalid = []
    for rule in rules:
        err = validatePermissionRuleString(rule)
        if err is None:
            valid.append(rule)
        else:
            invalid.append(rule)
    return valid, invalid


def validateSettingsJson(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate a settings dict. Returns a list of validation error dicts."""
    errors = []
    if 'model' in data and not isinstance(data['model'], str):
        errors.append({'path': ['model'], 'message': 'Must be a string'})
    if 'permissions' in data:
        perms = data['permissions']
        if not isinstance(perms, dict):
            errors.append({'path': ['permissions'], 'message': 'Must be an object'})
        else:
            for behavior in ('allow', 'deny', 'ask'):
                if behavior in perms:
                    if not isinstance(perms[behavior], list):
                        errors.append({'path': ['permissions', behavior], 'message': 'Must be an array'})
                    else:
                        for i, rule in enumerate(perms[behavior]):
                            err = validatePermissionRuleString(rule)
                            if err:
                                errors.append({'path': ['permissions', behavior, i], 'message': err})
    if 'theme' in data and data['theme'] not in VALID_THEMES:
        errors.append({'path': ['theme'], 'message': f"Must be one of: {', '.join(VALID_THEMES)}"})
    if 'verbose' in data and not isinstance(data['verbose'], bool):
        errors.append({'path': ['verbose'], 'message': 'Must be a boolean'})
    return errors
