"""Port of src/utils/settings/validateEditTool.ts"""
from __future__ import annotations
import json
import os
from typing import Optional, Dict, Any, List, Tuple


SETTINGS_EXTENSIONS = frozenset({'.json', '.jsonc'})


def _is_settings_json(file_path: str) -> bool:
    """Return True if the file path looks like a vivian settings file."""
    basename = os.path.basename(file_path)
    return basename in ('settings.json', 'settings.local.json')


def validateEditedSettingsFile(
    file_path: str,
    new_content: str,
) -> Optional[str]:
    """Validate the new content of an edited settings file.
    Returns an error message if invalid, None if OK."""
    if not _is_settings_json(file_path):
        return None
    try:
        data = json.loads(new_content)
    except json.JSONDecodeError as e:
        return f'Settings file has invalid JSON: {e}'
    if not isinstance(data, dict):
        return 'Settings file must contain a JSON object'
    from .validation import validateSettingsJson
    errors = validateSettingsJson(data)
    if not errors:
        return None
    from .validation import formatValidationErrors
    return f'Settings file has validation errors: {formatValidationErrors(errors)}'


def checkSettingsFileConsistency(
    file_path: str,
    new_content: str,
) -> Tuple[bool, Optional[str]]:
    """Check if edited settings are consistent. Returns (is_valid, error_message)."""
    err = validateEditedSettingsFile(file_path, new_content)
    if err is not None:
        return False, err
    return True, None
