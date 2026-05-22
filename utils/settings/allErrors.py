"""Port of src/utils/settings/allErrors.ts"""
from __future__ import annotations
from typing import Dict, Any, List, Optional

from .settings import getSettingsForSource
from .validation import validateSettingsJson


def getAllSettingsErrors() -> Dict[str, List[Dict[str, Any]]]:
    """Collect validation errors from all settings sources."""
    sources = ('userSettings', 'projectSettings', 'localSettings', 'policySettings')
    all_errors: Dict[str, List[Dict[str, Any]]] = {}
    for source in sources:
        data = getSettingsForSource(source)
        if data is None:
            continue
        errors = validateSettingsJson(data)
        if errors:
            all_errors[source] = errors
    return all_errors


def formatAllSettingsErrors(errors: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format all settings errors as a human-readable string."""
    lines = []
    for source, source_errors in errors.items():
        from .constants import getSettingSourceDisplayNameCapitalized
        name = getSettingSourceDisplayNameCapitalized(source)
        lines.append(f'{name} settings errors:')
        for err in source_errors:
            path = '.'.join(str(p) for p in err.get('path', []))
            msg = err.get('message', 'Invalid value')
            lines.append(f'  {path}: {msg}' if path else f'  {msg}')
    return '\n'.join(lines)


def hasAnySettingsErrors() -> bool:
    """Return True if any settings source has validation errors."""
    return bool(getAllSettingsErrors())
