"""Semantic boolean parsing — mirrors src/utils/semanticBoolean.ts"""
from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

_TRUE_LITERAL = "true"
_FALSE_LITERAL = "false"


def _default_boolean_validator(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError("Expected a boolean value")


def _coerce_semantic_boolean(value: Any) -> Any:
    if value == _TRUE_LITERAL:
        return True
    if value == _FALSE_LITERAL:
        return False
    return value


def semanticBoolean(inner: Optional[Callable[[Any], T]] = None) -> Callable[[Any], T]:
    validator = inner or _default_boolean_validator

    def wrapped(value: Any) -> T:
        return validator(_coerce_semantic_boolean(value))

    return wrapped


def parse_semantic_boolean(value: Any) -> Optional[bool]:
    """Parse only the TS-supported string literals "true" and "false"."""
    coerced = _coerce_semantic_boolean(value)
    if isinstance(coerced, bool):
        return coerced
    return None


def is_semantic_true(value: Any) -> bool:
    """Return True if value is the TS-supported truthy literal."""
    return value == _TRUE_LITERAL


def is_semantic_false(value: Any) -> bool:
    """Return True if value is the TS-supported falsy literal."""
    return value == _FALSE_LITERAL


semantic_boolean = semanticBoolean
