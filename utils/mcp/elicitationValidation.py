"""Elicitation schema validation — mirrors src/utils/mcp/elicitationValidation.ts"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

from .dateTimeParser import looks_like_iso8601, parse_natural_language_date_time

ValidationResult = Dict[str, Any]

# Format hints used in getFormatHint
_STRING_FORMATS: Dict[str, Dict[str, str]] = {
    "email": {"description": "email address", "example": "user@example.com"},
    "uri": {"description": "URI", "example": "https://example.com"},
    "date": {"description": "date", "example": "2024-03-15"},
    "date-time": {"description": "date-time", "example": "2024-03-15T14:30:00Z"},
}


# ---------------------------------------------------------------------------
# Schema type predicates
# ---------------------------------------------------------------------------

def is_enum_schema(schema: Dict[str, Any]) -> bool:
    """Return True if *schema* is a single-select enum (legacy ``enum`` or ``oneOf``)."""
    return schema.get("type") == "string" and ("enum" in schema or "oneOf" in schema)


isEnumSchema = is_enum_schema


def is_multi_select_enum_schema(schema: Dict[str, Any]) -> bool:
    """Return True if *schema* is a multi-select enum (``type: array`` with ``items.enum`` or ``items.anyOf``)."""
    if schema.get("type") != "array":
        return False
    items = schema.get("items")
    if not isinstance(items, dict):
        return False
    return "enum" in items or "anyOf" in items


isMultiSelectEnumSchema = is_multi_select_enum_schema


# ---------------------------------------------------------------------------
# Multi-select helpers
# ---------------------------------------------------------------------------

def get_multi_select_values(schema: Dict[str, Any]) -> List[str]:
    """Return the selectable values from a multi-select enum schema."""
    items = schema.get("items", {})
    if "anyOf" in items:
        return [item.get("const", "") for item in items["anyOf"]]
    if "enum" in items:
        return list(items["enum"])
    return []


getMultiSelectValues = get_multi_select_values


def get_multi_select_labels(schema: Dict[str, Any]) -> List[str]:
    """Return display labels from a multi-select enum schema."""
    items = schema.get("items", {})
    if "anyOf" in items:
        return [item.get("title", item.get("const", "")) for item in items["anyOf"]]
    if "enum" in items:
        return list(items["enum"])
    return []


getMultiSelectLabels = get_multi_select_labels


def get_multi_select_label(schema: Dict[str, Any], value: str) -> str:
    """Return the display label for *value* in a multi-select enum schema."""
    values = get_multi_select_values(schema)
    labels = get_multi_select_labels(schema)
    try:
        idx = values.index(value)
        return labels[idx] if idx < len(labels) else value
    except ValueError:
        return value


getMultiSelectLabel = get_multi_select_label


# ---------------------------------------------------------------------------
# Enum helpers
# ---------------------------------------------------------------------------

def get_enum_values(schema: Dict[str, Any]) -> List[str]:
    """Return enum values from an EnumSchema (``enum`` or ``oneOf`` format)."""
    if "oneOf" in schema:
        return [item.get("const", "") for item in schema["oneOf"]]
    if "enum" in schema:
        return list(schema["enum"])
    return []


getEnumValues = get_enum_values


def get_enum_labels(schema: Dict[str, Any]) -> List[str]:
    """Return display labels for an EnumSchema."""
    if "oneOf" in schema:
        return [item.get("title", item.get("const", "")) for item in schema["oneOf"]]
    if "enum" in schema:
        return list(schema.get("enumNames", schema["enum"]))
    return []


getEnumLabels = get_enum_labels


def get_enum_label(schema: Dict[str, Any], value: str) -> str:
    """Return the display label for *value* in an EnumSchema."""
    values = get_enum_values(schema)
    labels = get_enum_labels(schema)
    try:
        idx = values.index(value)
        return labels[idx] if idx < len(labels) else value
    except ValueError:
        return value


getEnumLabel = get_enum_label


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _plural(n: int, word: str) -> str:
    return word if n == 1 else f"{word}s"


def _validate_string(string_value: str, schema: Dict[str, Any]) -> ValidationResult:
    """Validate a string value against a string schema."""
    # Enum check
    if is_enum_schema(schema):
        allowed = get_enum_values(schema)
        if string_value in allowed:
            return {"value": string_value, "isValid": True}
        return {"isValid": False, "error": f"Must be one of: {', '.join(allowed)}"}

    # Length constraints
    min_len = schema.get("minLength")
    max_len = schema.get("maxLength")
    if min_len is not None and len(string_value) < min_len:
        return {"isValid": False, "error": f"Must be at least {min_len} {_plural(min_len, 'character')}"}
    if max_len is not None and len(string_value) > max_len:
        return {"isValid": False, "error": f"Must be at most {max_len} {_plural(max_len, 'character')}"}

    # Format constraints
    fmt = schema.get("format")
    if fmt == "email":
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', string_value):
            return {"isValid": False, "error": "Must be a valid email address, e.g. user@example.com"}
    elif fmt == "uri":
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://', string_value):
            return {"isValid": False, "error": "Must be a valid URI, e.g. https://example.com"}
    elif fmt == "date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', string_value):
            return {"isValid": False, "error": "Must be a valid date, e.g. 2024-03-15, today, next Monday"}
    elif fmt == "date-time":
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', string_value):
            return {"isValid": False, "error": "Must be a valid date-time, e.g. 2024-03-15T14:30:00Z, tomorrow at 3pm"}

    return {"value": string_value, "isValid": True}


def _validate_number(string_value: str, schema: Dict[str, Any]) -> ValidationResult:
    """Validate and coerce a string to number per schema constraints."""
    schema_type = schema.get("type", "number")
    is_integer = schema_type == "integer"

    try:
        num = float(string_value)
        if is_integer:
            if num != int(num):
                raise ValueError("not an integer")
            num = int(num)
    except (ValueError, TypeError):
        type_label = "an integer" if is_integer else "a number"
        return {"isValid": False, "error": f"Must be {type_label}"}

    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    type_label = "an integer" if is_integer else "a number"

    def fmt_n(n: float) -> str:
        return str(int(n)) if is_integer or n == int(n) else f"{n:.1f}"

    if minimum is not None and num < minimum:
        msg = (
            f"Must be {type_label} between {fmt_n(minimum)} and {fmt_n(maximum)}"
            if maximum is not None else f"Must be {type_label} >= {fmt_n(minimum)}"
        )
        return {"isValid": False, "error": msg}
    if maximum is not None and num > maximum:
        msg = (
            f"Must be {type_label} between {fmt_n(minimum)} and {fmt_n(maximum)}"
            if minimum is not None else f"Must be {type_label} <= {fmt_n(maximum)}"
        )
        return {"isValid": False, "error": msg}

    return {"value": int(num) if is_integer else num, "isValid": True}


def validate_elicitation_input(string_value: str, schema: Dict[str, Any]) -> ValidationResult:
    """Synchronously validate *string_value* against *schema*.

    Returns ``{"value": <parsed>, "isValid": True}`` on success or
    ``{"isValid": False, "error": "<message>"}`` on failure.
    """
    schema_type = schema.get("type")
    if schema_type == "string" or is_enum_schema(schema):
        return _validate_string(string_value, schema)
    if schema_type in ("number", "integer"):
        return _validate_number(string_value, schema)
    if schema_type == "boolean":
        lower = string_value.strip().lower()
        if lower in ("true", "1", "yes", "on"):
            return {"value": True, "isValid": True}
        if lower in ("false", "0", "no", "off"):
            return {"value": False, "isValid": True}
        return {"isValid": False, "error": "Must be true or false"}
    return {"isValid": False, "error": f"Unsupported schema type: {schema_type}"}


validateElicitationInput = validate_elicitation_input


# ---------------------------------------------------------------------------
# Format hints
# ---------------------------------------------------------------------------

def get_format_hint(schema: Dict[str, Any]) -> Optional[str]:
    """Return a human-readable hint string for *schema*'s format, or None."""
    schema_type = schema.get("type")
    if schema_type == "string":
        fmt = schema.get("format")
        if not fmt:
            return None
        info = _STRING_FORMATS.get(fmt)
        if info:
            return f"{info['description']}, e.g. {info['example']}"
        return None
    if schema_type in ("number", "integer"):
        is_integer = schema_type == "integer"

        def fmt_n(n: float) -> str:
            return str(int(n)) if is_integer or n == int(n) else f"{n:.1f}"

        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and maximum is not None:
            return f"({schema_type} between {fmt_n(minimum)} and {fmt_n(maximum)})"
        if minimum is not None:
            return f"({schema_type} >= {fmt_n(minimum)})"
        if maximum is not None:
            return f"({schema_type} <= {fmt_n(maximum)})"
        example = "42" if is_integer else "3.14"
        return f"({schema_type}, e.g. {example})"
    return None


getFormatHint = get_format_hint


# ---------------------------------------------------------------------------
# Date/time schema predicate
# ---------------------------------------------------------------------------

def is_date_time_schema(schema: Dict[str, Any]) -> bool:
    """Return True if *schema* is a string with ``date`` or ``date-time`` format."""
    return (
        schema.get("type") == "string"
        and schema.get("format") in ("date", "date-time")
    )


isDateTimeSchema = is_date_time_schema


# ---------------------------------------------------------------------------
# Async validation with NL date/time fallback
# ---------------------------------------------------------------------------

async def validate_elicitation_input_async(
    string_value: str,
    schema: Dict[str, Any],
    signal: object = None,
) -> ValidationResult:
    """Validate *string_value* asynchronously, attempting NL date parsing on failure.

    When the schema is a date/date-time format and the sync validation fails,
    this tries ``parse_natural_language_date_time`` before giving up.
    """
    sync_result = validate_elicitation_input(string_value, schema)
    if sync_result.get("isValid"):
        return sync_result

    if is_date_time_schema(schema) and not looks_like_iso8601(string_value):
        fmt = schema.get("format", "date")
        parse_result = await parse_natural_language_date_time(string_value, fmt, signal)
        if parse_result.get("success"):
            validated = validate_elicitation_input(parse_result["value"], schema)  # type: ignore[arg-type]
            if validated.get("isValid"):
                return validated

    return sync_result


validateElicitationInputAsync = validate_elicitation_input_async

