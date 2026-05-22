"""Semantic number parsing — mirrors src/utils/semanticNumber.ts"""
from __future__ import annotations

import math
import re
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

_DECIMAL_LITERAL_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _default_number_validator(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Expected a numeric value")
    if isinstance(value, (int, float)):
        numeric = float(value)
        if math.isfinite(numeric):
            return numeric
    raise ValueError("Expected a numeric value")


def _coerce_semantic_number(value: Any) -> Any:
    if isinstance(value, str) and _DECIMAL_LITERAL_RE.fullmatch(value):
        numeric = float(value)
        if math.isfinite(numeric):
            return numeric
    return value


def semanticNumber(inner: Optional[Callable[[Any], T]] = None) -> Callable[[Any], T]:
    validator = inner or _default_number_validator

    def wrapped(value: Any) -> T:
        return validator(_coerce_semantic_number(value))

    return wrapped


def parse_semantic_number(value: Any) -> Optional[float]:
    """Parse only the TS-supported decimal string literal format."""
    coerced = _coerce_semantic_number(value)
    if isinstance(coerced, bool):
        return None
    if isinstance(coerced, (int, float)):
        numeric = float(coerced)
        if math.isfinite(numeric):
            return numeric
    return None


def parse_semantic_integer(value: Any) -> Optional[int]:
    """Parse a string as an integer, returning None for invalid input."""
    num = parse_semantic_number(value)
    if num is None:
        return None
    return int(num)


semantic_number = semanticNumber

