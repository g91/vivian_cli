"""Form validation — mirrors src/hooks/useFormValidation.ts."""
from __future__ import annotations
from typing import Any

def useFormValidation(validators: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate form fields."""
    errors = {}
    
    def validate(field: str, value: str) -> bool:
        if validators and field in validators:
            is_valid = validators[field](value)
            if not is_valid:
                errors[field] = f"{field} is invalid"
            else:
                errors.pop(field, None)
            return is_valid
        return True
    
    return {
        "errors": errors,
        "validate": validate,
    }

use_form_validation = useFormValidation
