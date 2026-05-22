"""Port of src/utils/envValidation."""
from __future__ import annotations

from typing import Any, Dict


EnvVarValidationResult = Dict[str, Any]


def validateBoundedIntEnvVar(name, value, defaultValue, upperLimit):
    del name
    effective = defaultValue
    valid = True
    if value not in (None, ""):
        try:
            parsed = int(value)
            if parsed < 0:
                effective = 0
            else:
                effective = min(parsed, upperLimit)
        except (TypeError, ValueError):
            valid = False
            effective = defaultValue
    return {
        "effective": effective,
        "isValid": valid,
        "defaultValue": defaultValue,
        "upperLimit": upperLimit,
    }

